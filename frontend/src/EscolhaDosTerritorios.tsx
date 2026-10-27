import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { LoaderCircle, Plus, Search, Trash2, X } from "lucide-react";
import { pedirTerritorios, type FonteDoMotor, type MunicipioDaLista, type PainelCriterio, type PainelUniverso, type Premissas,
  type RespostaTerritorios } from "./painelApi";
import {
  LADOS, MAX_FILTROS, NOMES_DOS_FILTROS, NOMES_DOS_LADOS, NOTA_TPL11, OPERADORES_DO_FILTRO, REGIOES_DO_BRASIL,
  TEXTO_DE_APOIO_DOS_FILTROS, TEXTO_DOS_OPERADORES, UNIDADES_DOS_FILTROS, consultaParaOMotor, escreverLimites, escreverValorDoFiltro,
  formatarIndicador, fraseDaConsulta, generoDe, lerLimites, lerValorDoFiltro, mesmaConsulta, notaDaDistanciaDaConsulta, operadorDoCriterio,
  pendenciasDaConsulta, quantos, quantosCandidatos, textoDaPendencia, textoDasReferenciasUsadas, type ConsultaTerritorios,
  type FiltroDaConsulta, type GrupoInfo, type IndicadorDoFiltro, type Lado, type LadoDaConsulta, type OperadorDoFiltro,
  type RotulosTerritoriais, type TipoPartida,
} from "./painelModel";

// Janela "Escolha dos territórios" da Análise Espacial (27/10/2026, comando Seleção de Territórios; no lugar do painel Território
// de referência): base e referência são territórios irmãos, cada um com o mesmo seletor em três etapas (Partir de, Filtrar por,
// Escolher), numa janela com a frase-resumo fixa no alto, as abas "1 Base" e "2 Referência" (só a ativa aparece) e o rodapé com
// "Calcular" e a linha de estado. O rascunho da consulta é a fonte de verdade da janela; a frase sai dele por modelo
// (fraseDaConsulta). Toda contagem, prévia e lista vem do motor (POST /api/painel/territorios, pedido a cada mudança, com espera
// curta); a tela não seleciona, não conta e não mede distância. "Calcular" leva a consulta à análise (um passo do Desfazer).

export type EscolhaDosTerritoriosProps = {
  fonte: FonteDoMotor;
  /** A consulta calculada (null antes do primeiro "Calcular"). */
  aplicada: ConsultaTerritorios | null;
  /** A consulta com que a janela abre sem consulta calculada (consultaInicial). */
  inicial: ConsultaTerritorios;
  /** O que vai junto em todo pedido das contagens: a competência, a categoria, a seleção prévia (`base`, a escolha da Seleção de
   * Territórios) e, nas planilhas, as premissas e os rótulos. */
  pedido: { competencia: string; categoria: string; base?: PainelUniverso; premissas?: Premissas; rotulos?: RotulosTerritoriais };
  /** O contexto da análise, embaixo do título: a categoria profissional e a competência. */
  contexto: string;
  rotulos: RotulosTerritoriais; brasil: boolean; grupos: GrupoInfo[]; temPopulacao: boolean; nomes: Map<string, string>;
  /** O resultado da consulta calculada está à vista; `calculando`, o cálculo dela está em curso. */
  emDia: boolean; calculando: boolean;
  /** As referências que o motor usou no resultado à vista (os nomes, `referencia.membros`) e, com um só território na base, o nome
   * dele: a aba Referência diz quais candidatos ficaram como referência (27/10/2026). */
  usadas: { referencias: string[]; base: string | null } | null;
  /** Referência pedida na conversa por critério ("a de maior densidade como referência"): a aba Referência ganha o filtro do
   * atributo e do operador do pedido, com o valor para a pessoa preencher. */
  criterio?: PainelCriterio | null;
  faixas: number[]; onFaixas: (limites: number[]) => void;
  onCalcular: (consulta: ConsultaTerritorios) => void;
};

/** Opções do menu "Partir de"; "uma região" e "mais de uma região" (e os estados) são a mesma escolha na consulta, com uma ou mais. */
type OpcaoDePartida = "pais" | "regiao" | "regioes" | "uf" | "ufs" | "selecao_previa" | "mesma_uf_da_base" | "mesma_regiao_da_base";
const LIMITE_DA_LISTA = 100;
const ESPERA_DAS_CONTAGENS = 250;

const opcaoDe = (lado: LadoDaConsulta): OpcaoDePartida => {
  const { tipo, regioes, ufs } = lado.partir_de;
  if (tipo === "regioes") return regioes.length > 1 ? "regioes" : "regiao";
  if (tipo === "ufs") return ufs.length > 1 ? "ufs" : "uf";
  return tipo;
};
const tipoDa = (opcao: OpcaoDePartida): TipoPartida => opcao === "regiao" ? "regioes" : opcao === "uf" ? "ufs" : opcao;
const textosDosFiltros = (consulta: ConsultaTerritorios): Record<Lado, string[]> =>
  ({ base: consulta.base.filtros.map(f => escreverValorDoFiltro(f.valor)), referencia: consulta.referencia.filtros.map(f => escreverValorDoFiltro(f.valor)) });
const formatarInteiro = (n: number) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(n);

export default function EscolhaDosTerritorios(p: EscolhaDosTerritoriosProps) {
  const [rascunho, setRascunho] = useState<ConsultaTerritorios>(() => p.aplicada ?? p.inicial);
  const [aba, setAba] = useState<Lado>("base");
  const [opcoes, setOpcoes] = useState<Record<Lado, OpcaoDePartida>>(() => ({ base: opcaoDe((p.aplicada ?? p.inicial).base),
    referencia: opcaoDe((p.aplicada ?? p.inicial).referencia) }));
  const [textos, setTextos] = useState<Record<Lado, string[]>>(() => textosDosFiltros(p.aplicada ?? p.inicial));
  const [busca, setBusca] = useState<Record<Lado, string>>({ base: "", referencia: "" });
  const [resposta, setResposta] = useState<RespostaTerritorios | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [faixas, setFaixas] = useState(escreverLimites(p.faixas));
  useEffect(() => setFaixas(escreverLimites(p.faixas)), [p.faixas]);
  const unidade = p.rotulos.unidade, grupo = p.rotulos.grupo ?? { singular: "grupo", plural: "grupos" };
  const femUnidade = generoDe(unidade) === "f", femGrupo = generoDe(grupo) === "f";
  const temGrupos = p.grupos.length > 0;

  // A consulta calculada que muda por fora da janela (a conversa, o Desfazer, o Histórico) passa a ser o rascunho.
  const aplicadaJson = JSON.stringify(p.aplicada);
  const ultimaAplicada = useRef(aplicadaJson);
  useEffect(() => {
    if (aplicadaJson === ultimaAplicada.current) return;
    ultimaAplicada.current = aplicadaJson;
    const nova = p.aplicada ?? p.inicial;
    setRascunho(nova); setTextos(textosDosFiltros(nova));
    setOpcoes({ base: opcaoDe(nova.base), referencia: opcaoDe(nova.referencia) });
  }, [aplicadaJson]);
  // Critério da conversa: o filtro do atributo e do operador pedidos entra na Referência, sem valor (a pessoa completa).
  const criterioJson = JSON.stringify(p.criterio ?? null);
  useEffect(() => {
    const operador = operadorDoCriterio(p.criterio);
    if (!p.criterio || !operador) return;
    setAba("referencia");
    const ja = rascunho.referencia.filtros.some(f => f.indicador === p.criterio!.atributo && f.operador === operador);
    if (!ja) mudarFiltros("referencia", [...rascunho.referencia.filtros, { indicador: p.criterio.atributo, operador, valor: null }],
      [...textos.referencia, ""]);
  }, [criterioJson]);

  // Contagens do motor para o rascunho (e a lista para marcar do lado à vista, no modo "Só os que eu marcar").
  const listaPedida = rascunho[aba].escolha.modo === "marcados" ? { lado: aba, busca: busca[aba].trim(), limite: LIMITE_DA_LISTA } : undefined;
  const paraOMotor = consultaParaOMotor(rascunho);
  const chaveDoPedido = JSON.stringify([p.pedido, paraOMotor, listaPedida ?? null]);
  useEffect(() => {
    const controle = new AbortController();
    setCarregando(true);
    const timer = window.setTimeout(() => {
      pedirTerritorios(p.fonte, { ...p.pedido, consulta: paraOMotor, ...(listaPedida ? { lista: listaPedida } : {}) }, controle.signal)
        .then(corpo => { if (!controle.signal.aborted) { setResposta(corpo); setErro(null); } })
        .catch((exc: unknown) => { if (!controle.signal.aborted) setErro(exc instanceof Error ? exc.message : "Não foi possível contar os territórios."); })
        .finally(() => { if (!controle.signal.aborted) setCarregando(false); });
    }, ESPERA_DAS_CONTAGENS);
    return () => { controle.abort(); window.clearTimeout(timer); };
  }, [chaveDoPedido]);

  const pendencias = pendenciasDaConsulta(rascunho, p.rotulos);
  const frase = fraseDaConsulta(rascunho, { rotulos: p.rotulos, brasil: p.brasil, grupos: p.grupos, nomes: nomesConhecidos() });
  const primeiraFalta = LADOS.map(lado => pendencias[lado].length ? textoDaPendencia(lado, pendencias[lado][0]) : null).find(Boolean) ?? null;
  const mudou = !mesmaConsulta(rascunho, p.aplicada);
  const podeCalcular = !primeiraFalta && mudou;
  const estado = primeiraFalta ?? (mudou ? "A consulta mudou. Calcule para atualizar." : p.calculando ? "Calculando o resultado da consulta…"
    : p.emDia ? "Resultado em dia com a consulta." : "A consulta está calculada; o resultado aparece no gráfico.");

  /** Os nomes que a frase e os marcados usam: os do motor (lista e marcados) e os do catálogo da fonte. */
  function nomesConhecidos(): Map<string, string> {
    const nomes = new Map(p.nomes);
    for (const item of [...(resposta?.lista?.itens ?? []), ...(resposta?.base.marcados ?? []), ...(resposta?.referencia.marcados ?? [])])
      nomes.set(item.id, item.rotulo);
    return nomes;
  }
  function mudarLado(lado: Lado, parte: Partial<LadoDaConsulta>) {
    setRascunho(atual => ({ ...atual, [lado]: { ...atual[lado], ...parte } }));
  }
  function mudarFiltros(lado: Lado, filtros: FiltroDaConsulta[], novosTextos: string[]) {
    mudarLado(lado, { filtros });
    setTextos(atual => ({ ...atual, [lado]: novosTextos }));
  }
  function escolherPartida(lado: Lado, opcao: OpcaoDePartida) {
    setOpcoes(atual => ({ ...atual, [lado]: opcao }));
    const atual = rascunho[lado].partir_de;
    const tipo = tipoDa(opcao);
    // De "mais de uma" para "uma", fica a primeira marcada; o resto do rascunho continua guardado para voltar.
    const regioes = opcao === "regiao" ? atual.regioes.slice(0, 1) : atual.regioes;
    const ufs = opcao === "uf" ? atual.ufs.slice(0, 1) : atual.ufs;
    mudarLado(lado, { partir_de: { tipo, regioes, ufs } });
  }
  function alternarNaLista(lado: Lado, chave: "regioes" | "ufs", valor: string) {
    const atual = rascunho[lado].partir_de;
    const lista = atual[chave].includes(valor) ? atual[chave].filter(item => item !== valor) : [...atual[chave], valor];
    mudarLado(lado, { partir_de: { ...atual, [chave]: lista } });
  }
  function adicionarFiltro(lado: Lado, indicador: IndicadorDoFiltro) {
    mudarFiltros(lado, [...rascunho[lado].filtros, { indicador, operador: "<", valor: null }], [...textos[lado], ""]);
  }
  function mudarFiltro(lado: Lado, indice: number, parte: Partial<FiltroDaConsulta>, texto?: string) {
    const filtros = rascunho[lado].filtros.map((filtro, i) => i === indice ? { ...filtro, ...parte } : filtro);
    mudarFiltros(lado, filtros, texto === undefined ? textos[lado] : textos[lado].map((t, i) => i === indice ? texto : t));
  }
  function digitarValor(lado: Lado, indice: number, texto: string) {
    const filtro = rascunho[lado].filtros[indice];
    mudarFiltro(lado, indice, { valor: lerValorDoFiltro(texto, filtro.indicador) }, texto);
  }
  function removerFiltro(lado: Lado, indice: number) {
    mudarFiltros(lado, rascunho[lado].filtros.filter((_, i) => i !== indice), textos[lado].filter((_, i) => i !== indice));
  }
  function alternarMarcado(lado: Lado, id: string) {
    const escolha = rascunho[lado].escolha;
    const municipios = escolha.municipios.includes(id) ? escolha.municipios.filter(item => item !== id) : [...escolha.municipios, id];
    mudarLado(lado, { escolha: { ...escolha, municipios } });
  }
  function teclasDasAbas(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const proxima: Lado = aba === "base" ? "referencia" : "base";
    setAba(proxima);
    document.getElementById("territorios-aba-" + proxima)?.focus();
  }

  const contagem = (valor: number | null | undefined, sufixo = "") => valor === null || valor === undefined
    ? (carregando ? "Contando…" : "—") : quantos(valor, unidade) + sufixo;
  // Na Referência, o conjunto é dito como candidatos (27/10/2026): só o mais próximo de cada território da base fica como referência.
  const statusDaAba = (lado: Lado) => {
    if (pendencias[lado].length) return "incompleta";
    const final = resposta?.[lado].contagens.final;
    return final === null || final === undefined ? "…" : lado === "base" ? quantos(final, unidade) : quantosCandidatos(final, unidade);
  };
  const previaDoLado = (lado: Lado) => {
    const previa = resposta?.[lado].previa;
    if (pendencias[lado].length && !previa) return "Complete " + (lado === "base" ? "a base" : "a referência") + " para ver quantos entram.";
    if (!previa) return carregando ? "Contando…" : "";
    const quantosEntram = lado === "base" ? quantos(previa.total, unidade) + (previa.total === 1 ? " entra na base" : " entram na base")
      : quantosCandidatos(previa.total, unidade) + " a referência";
    const resto = previa.total - previa.nomes.length;
    return quantosEntram + (previa.nomes.length ? ": " + previa.nomes.join(", ") + (resto > 0 ? " e mais " +
      formatarInteiro(resto) : "") : "") + ".";
  };

  const seletor = (lado: Lado) => {
    const l = rascunho[lado], dados = resposta?.[lado], contagens = dados?.contagens;
    const opcao = opcoes[lado];
    const id = (sufixo: string) => "territorios-" + lado + "-" + sufixo;
    const relativa = l.partir_de.tipo === "mesma_uf_da_base" || l.partir_de.tipo === "mesma_regiao_da_base";
    const marcados: MunicipioDaLista[] = l.escolha.municipios.map(m => dados?.marcados.find(item => item.id === m)
      ?? { id: m, rotulo: nomesConhecidos().get(m) || m, uf: null, densidade: null });
    const lista = resposta?.lista?.lado === lado ? resposta.lista : null;
    const previa = resposta?.selecaoPrevia;
    return <div data-testid={"territorios-" + lado} className="territorios-seletor">
      <fieldset className="territorios-etapa" data-testid={id("partir")}>
        <legend>1. Partir de</legend>
        <select data-testid={id("partir-menu")} aria-label={"Partir de (" + NOMES_DOS_LADOS[lado] + ")"} value={opcao} className="analise-campo"
          onChange={event => escolherPartida(lado, event.target.value as OpcaoDePartida)}>
          <option value="pais">{p.brasil ? "Todo o país" : "Toda a planilha"}</option>
          {p.brasil && <option value="regiao">Uma região</option>}
          {p.brasil && <option value="regioes">Mais de uma região</option>}
          {temGrupos && <option value="uf">{femGrupo ? "Uma " : "Um "}{grupo.singular}</option>}
          {temGrupos && <option value="ufs">Mais de {femGrupo ? "uma " : "um "}{grupo.singular}</option>}
          <option value="selecao_previa">Seleção prévia{previa ? " (" + formatarInteiro(previa.total) + ")" : ""}</option>
          {lado === "referencia" && (p.brasil || temGrupos) && <optgroup label="Conforme a base">
            <option value="mesma_uf_da_base">{p.brasil ? "Mesma UF de cada município da base" : (femGrupo ? "Mesma " : "Mesmo ") + grupo.singular +
              " de cada " + unidade.singular + " da base"}</option>
            {p.brasil && <option value="mesma_regiao_da_base">Mesma região de cada município da base</option>}
          </optgroup>}
        </select>
        {opcao === "regiao" && <select data-testid={id("regiao")} aria-label="Região" value={l.partir_de.regioes[0] ?? ""} className="analise-campo"
          onChange={event => mudarLado(lado, { partir_de: { ...l.partir_de, regioes: event.target.value ? [event.target.value] : [] } })}>
          <option value="">Escolha a região</option>
          {REGIOES_DO_BRASIL.map(regiao => <option key={regiao.id} value={regiao.nome}>{regiao.nome}</option>)}
        </select>}
        {opcao === "regioes" && <div role="group" aria-label="Regiões" className="territorios-botoes" data-testid={id("regioes")}>
          {REGIOES_DO_BRASIL.map(regiao => <button key={regiao.id} type="button" aria-pressed={l.partir_de.regioes.includes(regiao.nome)}
            data-testid={id("regiao-opcao")} data-id={regiao.nome} onClick={() => alternarNaLista(lado, "regioes", regiao.nome)}>{regiao.nome}</button>)}
        </div>}
        {opcao === "uf" && <select data-testid={id("uf")} aria-label={grupo.singular} value={l.partir_de.ufs[0] ?? ""} className="analise-campo"
          onChange={event => mudarLado(lado, { partir_de: { ...l.partir_de, ufs: event.target.value ? [event.target.value] : [] } })}>
          <option value="">Escolha {femGrupo ? "a " : "o "}{grupo.singular}</option>
          {p.grupos.map(item => <option key={item.id} value={item.id}>{item.nome}</option>)}
        </select>}
        {opcao === "ufs" && <div role="group" aria-label={grupo.plural} className="territorios-botoes territorios-botoes-ufs" data-testid={id("ufs")}>
          {p.grupos.map(item => <button key={item.id} type="button" aria-pressed={l.partir_de.ufs.includes(item.id)} title={item.nome}
            data-testid={id("uf-opcao")} data-id={item.id} onClick={() => alternarNaLista(lado, "ufs", item.id)}>{item.sigla || item.nome}</button>)}
        </div>}
        {opcao === "selecao_previa" && <p className="territorios-apoio" data-testid={id("selecao-previa")}>{!previa ? "Contando…" : previa.total
          ? "Na Seleção de Territórios: " + previa.nomes.join(", ") + (previa.total > previa.nomes.length ? " e mais " +
            formatarInteiro(previa.total - previa.nomes.length) : "") + "."
          : "Nenhum território selecionado na Seleção de Territórios."}</p>}
        {relativa && <p className="territorios-apoio" data-testid={id("conforme-a-base")}>{l.partir_de.tipo === "mesma_uf_da_base"
          ? (p.brasil ? "Para cada município da base, só conta referência no próprio estado. Ex.: um município do Acre só procura referência no Acre."
            : "Para cada " + unidade.singular + " da base, só conta referência n" + (femGrupo ? "a própria " : "o próprio ") + grupo.singular + ".")
          : "Para cada município da base, só conta referência na própria região."} É diferente de escolher {p.brasil ? "um estado" :
          (femGrupo ? "uma " : "um ") + grupo.singular}, que vale igual para tod{femUnidade ? "as" : "os"} {femUnidade ? "as" : "os"} {unidade.plural} da base.</p>}
        <p className="territorios-contagem" data-testid={id("contagem-partir")}>{contagem(contagens?.partirDe)}</p>
      </fieldset>

      <fieldset className="territorios-etapa" data-testid={id("filtros")}>
        <legend>2. Filtrar por <span className="territorios-opcional">(opcional)</span></legend>
        {l.filtros.map((filtro, indice) => {
          const texto = textos[lado][indice] ?? "";
          const invalido = !!texto.trim() && filtro.valor === null;
          return <div key={indice} className="territorios-filtro" data-testid={id("filtro")} data-indicador={filtro.indicador}>
            <div className="territorios-filtro-linha">
              <select aria-label="Indicador" data-testid={id("filtro-indicador")} value={filtro.indicador} className="analise-campo"
                onChange={event => mudarFiltro(lado, indice, { indicador: event.target.value as IndicadorDoFiltro,
                  valor: lerValorDoFiltro(texto, event.target.value as IndicadorDoFiltro) })}>
                {(["densidade", "populacao", "quantidade"] as IndicadorDoFiltro[]).map(item => <option key={item} value={item}
                  disabled={item !== "quantidade" && !p.temPopulacao}>{NOMES_DOS_FILTROS[item]}</option>)}
              </select>
              <button type="button" className="analise-icone" data-testid={id("filtro-remover")} aria-label={"Remover o filtro de " +
                NOMES_DOS_FILTROS[filtro.indicador].toLocaleLowerCase("pt-BR")} onClick={() => removerFiltro(lado, indice)}>
                <Trash2 size={14} aria-hidden="true"/></button>
            </div>
            <div className="territorios-filtro-linha">
              <select aria-label="Operador" data-testid={id("filtro-operador")} value={filtro.operador} className="analise-campo"
                onChange={event => mudarFiltro(lado, indice, { operador: event.target.value as OperadorDoFiltro })}>
                {OPERADORES_DO_FILTRO.map(operador => <option key={operador} value={operador}>
                  {TEXTO_DOS_OPERADORES[operador]}</option>)}
              </select>
              <input aria-label="Valor" data-testid={id("filtro-valor")} inputMode="decimal" value={texto} className="analise-campo"
                aria-invalid={invalido} placeholder={filtro.indicador === "densidade" ? "0,5" : filtro.indicador === "populacao" ? "20.000" : "10"}
                onChange={event => digitarValor(lado, indice, event.target.value)}/>
              <span className="territorios-unidade">{UNIDADES_DOS_FILTROS[filtro.indicador]}</span>
            </div>
            {invalido && <p className="territorios-erro">{filtro.indicador === "populacao" || filtro.indicador === "quantidade"
              ? "Use um número inteiro não negativo." : "Use um número não negativo, com vírgula decimal (por exemplo, 0,5)."}</p>}
          </div>;
        })}
        <div className="territorios-adicionar">
          {(["densidade", "populacao", "quantidade"] as IndicadorDoFiltro[]).map(item => <button key={item} type="button"
            data-testid={id("mais-" + item)} className="analise-botao-secundario" disabled={l.filtros.length >= MAX_FILTROS ||
              (item !== "quantidade" && !p.temPopulacao)} onClick={() => adicionarFiltro(lado, item)}>
            <Plus size={13} aria-hidden="true"/>{NOMES_DOS_FILTROS[item]}</button>)}
        </div>
        <p className="territorios-apoio" data-testid={id("apoio-filtros")}>{TEXTO_DE_APOIO_DOS_FILTROS}</p>
        <p className="territorios-contagem" data-testid={id("contagem-filtros")}>{contagem(contagens?.filtros, contagens?.filtros === 1 ? " resta" : " restam")}
          {!!contagens?.naoAvaliaveis && " · " + quantos(contagens.naoAvaliaveis, unidade) + " com filtro não avaliável"}</p>
      </fieldset>

      <fieldset className="territorios-etapa" data-testid={id("escolher")}>
        <legend>3. Escolher</legend>
        <div role="radiogroup" aria-label={"Escolher (" + NOMES_DOS_LADOS[lado] + ")"} className="analise-segmentos">
          <button type="button" role="radio" aria-checked={l.escolha.modo === "todos"} data-testid={id("todos")}
            onClick={() => mudarLado(lado, { escolha: { ...l.escolha, modo: "todos" } })}>
            Todos que atendem{contagens?.filtros !== null && contagens?.filtros !== undefined ? " (" + formatarInteiro(contagens.filtros) + ")" : ""}</button>
          <button type="button" role="radio" aria-checked={l.escolha.modo === "marcados"} data-testid={id("marcados")}
            onClick={() => mudarLado(lado, { escolha: { ...l.escolha, modo: "marcados" } })}>Só os que eu marcar</button>
        </div>
        {l.escolha.modo === "marcados" && <>
          {marcados.length > 0 && <ul className="territorios-marcados" aria-label="Marcados">
            {marcados.map(item => <li key={item.id}><button type="button" data-testid={id("marcado")} data-id={item.id}
              className={"territorios-marcado" + (item.passa === false ? " territorios-marcado-fora" : "")}
              aria-label={"Tirar " + item.rotulo + " dos marcados"} title={item.passa === false ? "Não passa pelas etapas 1 e 2: não entra." : undefined}
              onClick={() => alternarMarcado(lado, item.id)}>{item.rotulo}<X size={12} aria-hidden="true"/></button></li>)}
          </ul>}
          <label className="territorios-busca"><Search size={14} aria-hidden="true"/>
            <input type="search" data-testid={id("busca")} value={busca[lado]} placeholder="Buscar pelo nome" aria-label="Buscar pelo nome"
              onChange={event => setBusca(atual => ({ ...atual, [lado]: event.target.value }))}/></label>
          <ul className="territorios-lista" data-testid={id("lista")} aria-label={"Quem passou pelas etapas 1 e 2"}>
            {(lista?.itens ?? []).map(item => <li key={item.id}><label className="analise-caixa">
              <input type="checkbox" data-testid={id("lista-opcao")} data-id={item.id} checked={l.escolha.municipios.includes(item.id)}
                onChange={() => alternarMarcado(lado, item.id)}/>
              <span className="territorios-lista-nome">{item.rotulo}</span>
              <span className="territorios-lista-dado">{formatarIndicador(item.densidade, "densidade")}</span></label></li>)}
          </ul>
          <p className="territorios-apoio" data-testid={id("lista-total")}>{!lista ? (carregando ? "Buscando…" : "")
            : !lista.total ? "Ninguém passou pelas etapas 1 e 2" + (lista.busca ? " com esse nome." : ".")
            : lista.total > lista.itens.length ? "Mostrando " + formatarInteiro(lista.itens.length) + " de " + formatarInteiro(lista.total) +
              ": use a busca pelo nome." : formatarInteiro(lista.total) + (lista.total === 1 ? " passou" : " passaram") + " pelas etapas 1 e 2."}</p>
        </>}
        <p className="territorios-contagem" data-testid={id("contagem-final")}>{contagem(contagens?.final)}</p>
      </fieldset>

      <p className="territorios-previa" data-testid={id("previa")}>{previaDoLado(lado)}</p>
      {lado === "referencia" && !pendencias.referencia.length && <p className="territorios-apoio" data-testid="territorios-referencia-usadas">
        {textoDasReferenciasUsadas({ rotulos: p.rotulos, brasil: p.brasil, grupos: p.grupos, tipo: l.partir_de.tipo,
          candidatos: contagens?.final ?? null, usadas: !mudou && p.emDia ? p.usadas : null })}</p>}
      {lado === "referencia" && <div className="territorios-notas">
        <p data-testid="territorios-nota-distancia">{notaDaDistanciaDaConsulta(p.rotulos)}</p>
        <p className="territorios-apoio">{NOTA_TPL11}</p>
        <fieldset className="territorios-faixas">
          <legend>Faixas de distância (opcional)</legend>
          <p className="territorios-apoio">Limites em km, separados por ponto e vírgula (por exemplo, 0; 100; 300). A análise conta quantos ficam
            em cada faixa (CAP-ESP-03).</p>
          <div className="flex flex-wrap gap-2">
            <input data-testid="analise-faixas-distancia" value={faixas} onChange={event => setFaixas(event.target.value)} inputMode="decimal"
              className="analise-campo w-40" aria-label="Limites das faixas de distância (km)"/>
            <button type="button" data-testid="analise-faixas-distancia-aplicar" className="analise-botao-secundario"
              disabled={lerLimites(faixas).length < 2 && !!faixas.trim()} onClick={() => p.onFaixas(lerLimites(faixas))}>
              {faixas.trim() ? "Aplicar faixas" : "Sem faixas"}</button>
          </div>
        </fieldset>
      </div>}
    </div>;
  };

  return <section data-testid="analise-referencia" aria-label="Escolha dos territórios" className="territorios">
    <p className="territorios-contexto" data-testid="territorios-contexto">{p.contexto}</p>
    <p className="territorios-frase" data-testid="territorios-frase" aria-live="polite">
      <button type="button" data-testid="territorios-frase-base" data-incompleta={frase.base.incompleta}
        className={"territorios-trecho" + (frase.base.incompleta ? " territorios-trecho-incompleto" : "")} onClick={() => setAba("base")}
        title="Abrir a aba Base">{frase.base.texto}</button>
      <span aria-hidden="true"> → </span><span>referência: </span>
      <button type="button" data-testid="territorios-frase-referencia" data-incompleta={frase.referencia.incompleta}
        className={"territorios-trecho" + (frase.referencia.incompleta ? " territorios-trecho-incompleto" : "")} onClick={() => setAba("referencia")}
        title="Abrir a aba Referência">{frase.referencia.texto}</button>
    </p>
    <div role="tablist" aria-label="Territórios" className="territorios-abas">
      {LADOS.map((lado, indice) => <button key={lado} type="button" role="tab" id={"territorios-aba-" + lado} aria-selected={aba === lado}
        aria-controls="territorios-painel" tabIndex={aba === lado ? 0 : -1} data-testid={"territorios-aba-" + lado}
        className="territorios-aba" onClick={() => setAba(lado)} onKeyDown={teclasDasAbas}
        title={pendencias[lado].length ? textoDaPendencia(lado, pendencias[lado][0]) : undefined}>
        <span className="territorios-aba-nome">{indice + 1} {NOMES_DOS_LADOS[lado]}</span>
        <span data-testid={"territorios-status-" + lado} className={"territorios-aba-status" + (pendencias[lado].length ? " territorios-aba-incompleta" : "")}>
          {statusDaAba(lado)}</span>
      </button>)}
    </div>
    {erro && <p role="alert" data-testid="territorios-erro" className="territorios-erro">Não foi possível contar os territórios: {erro}</p>}
    <div role="tabpanel" id="territorios-painel" aria-labelledby={"territorios-aba-" + aba} className="territorios-painel">{seletor(aba)}</div>
    <div className="territorios-rodape" data-testid="territorios-rodape">
      <button type="button" data-testid="territorios-calcular" className="analise-botao-primario" disabled={!podeCalcular}
        onClick={() => p.onCalcular(paraOMotor)}>Calcular</button>
      <p role="status" data-testid="territorios-estado" data-pendente={!!primeiraFalta}
        className={"territorios-estado" + (primeiraFalta ? " territorios-estado-pendente" : "")}>
        {carregando && !primeiraFalta && <LoaderCircle size={13} className="animate-spin" aria-hidden="true"/>}{estado}</p>
    </div>
  </section>;
}
