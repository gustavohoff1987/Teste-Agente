import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { ChartScatter, ChevronDown, ChevronRight, Download, LoaderCircle, Map as IconeDoMapa, SlidersHorizontal, Table } from "lucide-react";
import { BolhasDoContexto, MapaDosSinais, SerieDaTaxa } from "./DetectorGraficos";
import { ErroDoMotor, pedirAoMotor, type FonteDoMotor } from "./painelApi";
import {
  FILTROS_DE_FENOMENO, NOMES_DAS_CLASSES, NOMES_DOS_PARAMETROS, ROTULOS_DOS_PORTES, SEM_FILTROS, TEXTO_LIMITES_PROVISORIOS, TEXTO_SINAIS_RELATIVOS, competenciaCurta,
  csvDoDetector, filtrarLinhas, formatarInteiro, formatarPct, metodoDoDetector, normalizarDetalhe, normalizarDetector, ordenarLinhas,
  parametrosPersonalizados, textoDaUltima, textoDoRegistro, tipoDoTerritorio, trechoDoContexto, trechoEstrutural, trechosCombinados,
  trechosDaComparacao, trechosDaTrajetoria, trechosDoRitmo, formatarTaxa, medicos, alvoDoSimulador, patamarARecuperar,
  type AlvoDoSimulador, type ClasseDoSinal, type DetalheDoDetector, type FiltrosDoDetector, type LinhaDoDetector, type OpcoesDoDetector, type OrdemDoDetector,
  type ParametrosDoDetector, type RespostaDoDetector, type SelecaoDasFerramentas, type Trecho,
} from "./detectorModel";

// Detector de Sinais Territoriais (comando V22, Eixo II, etapas 3 e 5; Docs/DETECTOR_DE_SINAIS.md). A tela mostra a situação mais
// recente da janela para os territórios da seleção em uso: a condição estrutural, a trajetória, o ritmo e a instabilidade, a
// comparação relativa (taxa por habitante, posição e defasagem ante a referência), o contexto geográfico, os sinais combinados, a
// qualidade do registro e a última observação. Os fenômenos 8 a 12 aparecem também em gráfico e mapa (DetectorGraficos.tsx, com os
// componentes do Agente); a tabela fica como detalhe. Há os filtros por fenômeno, porte e período; os detalhes de cada território (o que foi observado, o
// critério, quanto difere do habitual, o que significa, o que não significa, as limitações do dado e a qualidade do registro), com o
// histórico de sinais à parte; e os parâmetros personalizados, sempre marcados como exploratórios. Todo número e todo texto de
// resultado vêm do motor (POST /api/detector), que calcula sem o provedor de IA. A tela só filtra, ordena e desenha.

const POR_PAGINA = 50;
type Props = {
  fonte: FonteDoMotor;
  /** A seleção em uso (a da Seleção de Territórios); null sem territórios. */
  selecao: SelecaoDasFerramentas | null;
  resumoDaSelecao: string;
  onAlterarSelecao: () => void;
  /** Abre o território no Simulador de Cenários, com o contexto analítico (a data avaliada, a janela escolhida e os sinais à vista). */
  onAbrirNoSimulador?: (alvo: AlvoDoSimulador) => void;
  /** "Simular recuperação": abre o Simulador com o território e, como meta hipotética e editável, o patamar anterior (decisão D-B). */
  onSimularRecuperacao?: (alvo: AlvoDoSimulador, patamar: number) => void;
};
type Vista = "bolhas" | "mapa" | "tabela";

function baixar(nome: string, corpo: string, tipo: string) {
  const url = URL.createObjectURL(new Blob([corpo], { type: tipo }));
  const link = document.createElement("a");
  link.href = url; link.download = nome; link.click();
  URL.revokeObjectURL(url);
}

/** A intensidade do sinal, com o nome por extenso (não só a cor). */
function Intensidade({ classe }: { classe: ClasseDoSinal }) {
  return <span data-testid="detector-intensidade" data-classe={classe} className={"ferramenta-intensidade ferramenta-intensidade-" + classe}>
    {NOMES_DAS_CLASSES[classe]}</span>;
}
function TrechoDaLinha({ trecho }: { trecho: Trecho }) {
  return <span data-testid={"detector-" + trecho.chave} className="ferramenta-trecho">
    <span>{trecho.texto}</span>
    {trecho.classe && <Intensidade classe={trecho.classe}/>}
    {trecho.apoio && <span className="ferramenta-apoio">{trecho.apoio}</span>}
  </span>;
}

/** A série observada de um território: só os registros reais (janeiro e junho), com as marcas de registro. Sem linha ajustada. */
function SerieObservada({ detalhe }: { detalhe: DetalheDoDetector }) {
  const pontos = detalhe.serie;
  const valores = pontos.map(ponto => ponto.valor).filter((valor): valor is number => valor !== null);
  if (!valores.length) return <p className="ferramenta-apoio">Sem registros na série.</p>;
  const largura = 640, altura = 170, esquerda = 44, direita = 34, topo = 12, base = 34;
  const maximo = Math.max(...valores, 1);
  const x = (indice: number) => esquerda + (largura - esquerda - direita) * (pontos.length > 1 ? indice / (pontos.length - 1) : 0.5);
  const y = (valor: number) => topo + (altura - topo - base) * (1 - valor / maximo);
  const trechos: string[] = [];
  let atual: string[] = [];
  pontos.forEach((ponto, indice) => {
    if (ponto.valor === null) { if (atual.length > 1) trechos.push(atual.join(" ")); atual = []; return; }
    atual.push((atual.length ? "L" : "M") + x(indice).toFixed(1) + "," + y(ponto.valor).toFixed(1));
  });
  if (atual.length > 1) trechos.push(atual.join(" "));
  const inicioDaJanela = pontos.findIndex(ponto => ponto.competencia === detalhe.janela.inicio);
  return <figure data-testid="detector-serie" className="ferramenta-serie">
    <svg viewBox={"0 0 " + largura + " " + altura} width="100%" role="img"
      aria-label={"Série observada de " + detalhe.rotulo + ": " + pontos.map(ponto => competenciaCurta(ponto.competencia) + " " +
        (ponto.valor === null ? "sem registro" : ponto.valor)).join("; ")}>
      {inicioDaJanela > 0 && <rect x={esquerda} y={topo} width={x(inicioDaJanela) - esquerda} height={altura - topo - base} className="ferramenta-serie-fora"/>}
      <line x1={esquerda} x2={largura - direita} y1={altura - base} y2={altura - base} className="ferramenta-serie-eixo"/>
      <text x={esquerda - 6} y={y(maximo) + 4} textAnchor="end" className="ferramenta-serie-texto">{formatarInteiro(maximo)}</text>
      <text x={esquerda - 6} y={altura - base + 4} textAnchor="end" className="ferramenta-serie-texto">0</text>
      {trechos.map((caminho, indice) => <path key={indice} d={caminho} className="ferramenta-serie-linha"/>)}
      {pontos.map((ponto, indice) => ponto.valor === null
        ? <text key={ponto.competencia} x={x(indice)} y={altura - base - 6} textAnchor="middle" className="ferramenta-serie-texto"><title>
          {competenciaCurta(ponto.competencia)}: sem registro (ausência de dado, não é zero)</title>×</text>
        : <circle key={ponto.competencia} data-testid="detector-serie-ponto" data-competencia={ponto.competencia} data-marca={ponto.marca ?? ""}
          cx={x(indice)} cy={y(ponto.valor)} r={ponto.marca ? 4.5 : 3}
          className={"ferramenta-serie-ponto" + (ponto.marca ? " ferramenta-serie-ponto-marcado" : "")}>
          <title>{competenciaCurta(ponto.competencia) + ": " + formatarInteiro(ponto.valor) + (ponto.estado === "zero_confirmado" ? " (zero confirmado)" : "") +
            (ponto.marca === "pico_que_volta" ? " · pico que volta" : ponto.marca === "quebra_de_fonte" ? " · quebra de fonte"
              : ponto.marca === "verificar_registro" ? " · verificar registro" : "")}</title></circle>)}
      {pontos.map((ponto, indice) => ponto.competencia.endsWith("06") && (indice === pontos.length - 1 || Number(ponto.competencia.slice(0, 4)) % 2 === 0)
        ? <text key={"a" + ponto.competencia} x={x(indice)} y={altura - 12} textAnchor="middle" className="ferramenta-serie-texto">
          {competenciaCurta(ponto.competencia)}</text> : null)}
    </svg>
    <figcaption className="ferramenta-apoio">Registros observados (janeiro e junho). Pontos maiores: registro com marca (pico que volta, quebra de fonte ou
      “verificar registro”). ×: sem registro. Nenhuma linha é ajustada, e nada é estimado entre os registros.</figcaption>
  </figure>;
}

const CAMPOS_DO_DETALHE: [keyof DetalheDoDetector["fenomenos"][number], string][] = [
  ["observado", "O que foi observado"], ["criterio", "Qual critério"], ["habitual", "Quanto difere do habitual"], ["significa", "O que significa"],
  ["naoSignifica", "O que não significa"], ["limitacoes", "Limitações do dado"], ["qualidade", "Qualidade do registro"]];

function DetalheDoTerritorio({ detalhe, patamar, onAbrirNoSimulador, onSimularRecuperacao }: { detalhe: DetalheDoDetector;
  /** O patamar anterior do território (fenômeno 7), quando ele está abaixo dele: a meta hipotética de "Simular recuperação". */
  patamar: number | null; onAbrirNoSimulador?: () => void; onSimularRecuperacao?: () => void }) {
  const [aberto, setAberto] = useState<string | null>(detalhe.fenomenos.find(f => f.classe)?.chave ?? detalhe.fenomenos[0]?.chave ?? null);
  const [verHistorico, setVerHistorico] = useState(false);
  return <div data-testid="detector-detalhe" data-id={detalhe.id} className="ferramenta-detalhe">
    <p className="ferramenta-apoio">Contagem: {detalhe.unidade}.{detalhe.membros.length > 0 && " Componentes: " + detalhe.membros.join(", ") + "."}
      {detalhe.depoisDaQuebra && " Os indicadores deste território começam em " + competenciaCurta(detalhe.inicioDoTerritorio) + ", depois da quebra de fonte."}</p>
    <SerieObservada detalhe={detalhe}/>
    <SerieDaTaxa detalhe={detalhe}/>
    <ul className="ferramenta-fenomenos" aria-label={"Fenômenos de " + detalhe.rotulo}>
      {detalhe.fenomenos.map(f => <li key={f.chave} data-testid="detector-fenomeno" data-chave={f.chave} data-estado={f.estado} className="ferramenta-fenomeno">
        <button type="button" className="ferramenta-fenomeno-cabeca" aria-expanded={aberto === f.chave}
          onClick={() => setAberto(atual => atual === f.chave ? null : f.chave)}>
          {aberto === f.chave ? <ChevronDown size={15} aria-hidden="true"/> : <ChevronRight size={15} aria-hidden="true"/>}
          <span className="ferramenta-fenomeno-nome"><span className="ferramenta-apoio">{f.dimensao} · fenômeno {f.numero}</span>{f.nome}</span>
          <span data-testid="detector-fenomeno-situacao" className="ferramenta-fenomeno-situacao">{f.situacao}</span>
        </button>
        {aberto === f.chave && <dl className="ferramenta-fenomeno-corpo">
          {CAMPOS_DO_DETALHE.map(([campo, rotulo]) => <div key={campo} data-testid={"detector-campo-" + campo}>
            <dt>{rotulo}</dt><dd>{String(f[campo])}</dd></div>)}
        </dl>}
      </li>)}
    </ul>
    <div className="ferramenta-detalhe-acoes">
      <button type="button" data-testid="detector-historico-botao" className="analise-botao-secundario" aria-expanded={verHistorico}
        onClick={() => setVerHistorico(valor => !valor)}>{verHistorico ? "Fechar o histórico de sinais" : "Ver o histórico de sinais"}</button>
      {onAbrirNoSimulador && <button type="button" data-testid="detector-abrir-no-simulador" className="analise-botao-secundario"
        title="Leva este território ao Simulador de Cenários, com a data avaliada, a janela escolhida e os sinais à vista" onClick={onAbrirNoSimulador}>
        Abrir no Simulador</button>}
      {onSimularRecuperacao && patamar !== null && <button type="button" data-testid="detector-simular-recuperacao" className="analise-botao-secundario"
        title={"Abre o Simulador com a meta hipotética de voltar ao patamar de " + formatarTaxa(patamar).replace(/,00$/, "") + " médicos; a meta pode ser trocada"}
        onClick={onSimularRecuperacao}>Simular recuperação</button>}
    </div>
    {onSimularRecuperacao && patamar !== null && <p data-testid="detector-recuperacao-apoio" className="ferramenta-apoio">“Simular recuperação” abre o
      Simulador de Cenários com uma meta hipotética: voltar ao patamar de {medicos(Math.round(patamar))} (a maior média de dois anos seguidos antes
      dos registros mais recentes). A meta é uma hipótese que você pode trocar; o resultado é um cenário, não uma previsão.</p>}
    {verHistorico && <div className="ferramenta-rolagem"><table data-testid="detector-historico" className="analise-tabela ferramenta-tabela">
      <caption className="ferramenta-apoio">Histórico de sinais na janela: cada data avaliada só com o que era conhecido nela.</caption>
      <thead><tr><th scope="col">Registro</th><th scope="col">Médicos</th><th scope="col">Condição estrutural</th>
        <th scope="col">Perda desde o registro anterior</th><th scope="col">Patamar anterior</th><th scope="col">Série de junho</th></tr></thead>
      <tbody>{detalhe.historico.map(passo => <tr key={passo.competencia} data-competencia={passo.competencia}>
        <th scope="row">{competenciaCurta(passo.competencia)}</th>
        <td>{passo.valor === null ? "sem registro" : formatarInteiro(passo.valor)}</td>
        <td>{passo.estrutural ? <Intensidade classe={passo.estrutural}/> : "—"}</td>
        <td>{passo.perda ? <>{"−" + formatarInteiro(Math.abs(passo.perda.delta)) + (passo.perda.pct !== null ? " (−" + formatarPct(passo.perda.pct) + ")" : "")}{" "}
          {passo.perda.classe ? <Intensidade classe={passo.perda.classe}/> : <span className="ferramenta-apoio">
            {passo.perda.estado === "descontinuidade_de_registro" ? "descontinuidade de registro" : passo.perda.estado === "nao_calibrado"
              ? "sem classificação" : "sem alerta"}</span>}</> : "—"}</td>
        <td>{passo.patamar.diferencaPct === null ? "—" : <>{formatarPct(passo.patamar.diferencaPct) + (passo.patamar.diferencaPct < 0 ? " abaixo" : " acima")}{" "}
          {passo.patamar.classe && <Intensidade classe={passo.patamar.classe}/>}</>}</td>
        <td>{passo.declinio === null ? "" : [(passo.declinio.reducoes ?? 0) >= 2 ? passo.declinio.reducoes + " quedas seguidas" +
          (passo.declinio.sinal ? " (sinal " + (passo.declinio.sinal === "muito_forte" ? "muito forte" : "forte") + ")" : "") : "",
          passo.desaceleracao?.desacelera ? "desaceleração do crescimento" : ""].filter(Boolean).join(" · ") || "—"}</td>
      </tr>)}</tbody>
    </table></div>}
  </div>;
}

export default function DetectorDeSinais(p: Props) {
  const [janela, setJanela] = useState<{ inicio?: string; fim?: string }>({});
  const [parametros, setParametros] = useState<ParametrosDoDetector | null>(null);
  const [resposta, setResposta] = useState<RespostaDoDetector | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [tentativa, setTentativa] = useState(0);
  const [filtros, setFiltros] = useState<FiltrosDoDetector>(SEM_FILTROS);
  const [ordem, setOrdem] = useState<OrdemDoDetector>("intensidade");
  const [pagina, setPagina] = useState(0);
  const [aberto, setAberto] = useState<string | null>(null);
  const [detalhes, setDetalhes] = useState<Record<string, DetalheDoDetector | { erro: string }>>({});
  const [verParametros, setVerParametros] = useState(false);
  const [rascunho, setRascunho] = useState<Record<string, Record<string, string>>>({});
  const [verMetodo, setVerMetodo] = useState(false);
  const [vista, setVista] = useState<Vista>("bolhas");
  const cache = useRef(new Map<string, RespostaDoDetector>());

  const pedido: OpcoesDoDetector | null = useMemo(() => p.selecao ? { ...p.selecao, ...(janela.inicio || janela.fim ? { janela } : {}),
    ...(parametros ? { parametros } : {}) } : null, [p.selecao, janela, parametros]);
  const chave = pedido ? p.fonte.datasetVersion + "::" + JSON.stringify(pedido) : "";

  // A tabela: pedida ao motor a cada mudança da seleção, da janela ou dos parâmetros; a resposta de um pedido igual vem da memória.
  useEffect(() => {
    setAberto(null); setDetalhes({}); setPagina(0);
    if (!pedido) { setResposta(null); setErro(null); setCarregando(false); return; }
    const guardada = cache.current.get(chave);
    if (guardada) { setResposta(guardada); setErro(null); setCarregando(false); return; }
    const controle = new AbortController();
    setCarregando(true); setErro(null);
    pedirAoMotor(p.fonte, "/api/detector", pedido, controle.signal)
      .then(bruto => {
        if (controle.signal.aborted) return;
        const lida = normalizarDetector(bruto);
        cache.current.set(chave, lida);
        while (cache.current.size > 6) cache.current.delete(cache.current.keys().next().value as string);
        setResposta(lida);
      })
      .catch((exc: unknown) => {
        if (controle.signal.aborted) return;
        setErro(exc instanceof ErroDoMotor || exc instanceof Error ? exc.message : "Não foi possível calcular os sinais.");
      })
      .finally(() => { if (!controle.signal.aborted) setCarregando(false); });
    return () => controle.abort();
  }, [chave, tentativa]);

  // Os detalhes de um território, pedidos ao abrir a linha.
  useEffect(() => {
    if (!aberto || !pedido || detalhes[aberto]) return;
    const controle = new AbortController(), id = aberto;
    pedirAoMotor(p.fonte, "/api/detector", { ...pedido, detalhe: id }, controle.signal)
      .then(bruto => { if (!controle.signal.aborted) setDetalhes(atual => ({ ...atual, [id]: normalizarDetalhe(bruto) })); })
      .catch((exc: unknown) => { if (!controle.signal.aborted) setDetalhes(atual => ({ ...atual,
        [id]: { erro: exc instanceof Error ? exc.message : "Não foi possível abrir os detalhes." } })); });
    return () => controle.abort();
  }, [aberto, chave]);

  const filtradas = useMemo(() => resposta ? ordenarLinhas(filtrarLinhas(resposta.linhas, filtros), ordem) : [], [resposta, filtros, ordem]);
  const paginas = Math.max(1, Math.ceil(filtradas.length / POR_PAGINA));
  const paginaAtual = Math.min(pagina, paginas - 1);
  const naPagina = filtradas.slice(paginaAtual * POR_PAGINA, (paginaAtual + 1) * POR_PAGINA);
  const competencias = resposta?.competencias ?? [];
  const inicioEmUso = janela.inicio ?? resposta?.janela.inicio ?? "", fimEmUso = janela.fim ?? resposta?.janela.fim ?? "";
  const mudarFiltros = (parte: Partial<FiltrosDoDetector>) => { setFiltros(atual => ({ ...atual, ...parte })); setPagina(0); };
  /** Abre os detalhes de um território a partir do gráfico ou do mapa: a linha dele vai para a página à vista. */
  function abrirDoDesenho(id: string) {
    const posicao = filtradas.findIndex(linha => linha.id === id);
    if (posicao < 0) return;
    setPagina(Math.floor(posicao / POR_PAGINA));
    setAberto(id);
    requestAnimationFrame(() => document.querySelector('[data-testid="detector-linha"][data-id="' + id + '"]')?.scrollIntoView({ block: "center" }));
  }

  function aplicarParametros() {
    if (!resposta) return;
    const emEdicao: ParametrosDoDetector = {};
    for (const [grupo, campos] of Object.entries(resposta.parametros.editaveis)) for (const chaveDoCampo of Object.keys(campos)) {
      const digitado = rascunho[grupo]?.[chaveDoCampo];
      const valor = digitado === undefined ? resposta.parametros.emUso[grupo]?.[chaveDoCampo] : Number(digitado.replace(",", "."));
      if (typeof valor === "number" && Number.isFinite(valor)) (emEdicao[grupo] ??= {})[chaveDoCampo] = valor;
    }
    setParametros(parametrosPersonalizados(resposta.parametros.padrao, emEdicao));
    setRascunho({});
  }

  const cabecalho = <header className="ferramenta-cabecalho">
    <h2 id="detector-titulo" data-testid="detector-titulo" tabIndex={-1} className="analise-titulo">Detector de Sinais Territoriais</h2>
    <p className="analise-subtitulo">A situação mais recente de cada território da seleção: o que os registros mostram, se a mudança é incomum para
      territórios parecidos e a intensidade do sinal. Descreve os registros de médicos; não diz se o atendimento é suficiente nem onde prover.</p>
  </header>;

  if (!p.selecao) return <section data-testid="detector" data-estado="sem-selecao" aria-labelledby="detector-titulo" className="ferramenta">
    {cabecalho}
    <p data-testid="detector-sem-selecao" role="status" className="analise-motivo">Nenhum território selecionado.{" "}
      <button type="button" className="analise-link" onClick={p.onAlterarSelecao}>Selecionar os territórios</button></p>
  </section>;

  const resumo = resposta?.resumo;
  const contagem = (rotulo: string, n: number | undefined, testid: string) => n ? <span data-testid={testid} className="ferramenta-contagem">
    <strong className="tabular-nums">{formatarInteiro(n)}</strong> {rotulo}</span> : null;
  return <section data-testid="detector" data-estado={carregando ? "carregando" : erro ? "erro" : resposta ? "pronto" : "vazio"}
    data-exploratorio={resposta?.exploratorio ? "true" : "false"} aria-labelledby="detector-titulo" aria-busy={carregando || undefined} className="ferramenta">
    {cabecalho}
    {resposta && <p data-testid="detector-data" role="note" className="ferramenta-aviso">Registro mais recente da base: <strong>{competenciaCurta(resposta.janela.ultimoRegistroDaBase)}</strong>.
      Os sinais descrevem a situação até {competenciaCurta(resposta.janela.fim)}, não a de hoje. A base só tem médicos, com registros de janeiro e junho.</p>}

    <div className="ferramenta-controles analise-nao-imprimir" role="group" aria-label="Período, filtros e ordem">
      <label className="analise-rotulo-campo">Janela: de
        <select data-testid="detector-janela-inicio" className="analise-campo" value={inicioEmUso} disabled={!competencias.length}
          onChange={event => setJanela(atual => ({ ...atual, inicio: event.target.value }))}>
          {competencias.filter(c => !fimEmUso || c <= fimEmUso).map(c => <option key={c} value={c}>{competenciaCurta(c)}</option>)}
        </select></label>
      <label className="analise-rotulo-campo">até
        <select data-testid="detector-janela-fim" className="analise-campo" value={fimEmUso} disabled={!competencias.length}
          onChange={event => setJanela(atual => ({ ...atual, fim: event.target.value }))}>
          {competencias.filter(c => !inicioEmUso || c >= inicioEmUso).map(c => <option key={c} value={c}>{competenciaCurta(c)}</option>)}
        </select></label>
      <label className="analise-rotulo-campo">Fenômeno
        <select data-testid="detector-filtro-fenomeno" className="analise-campo" value={filtros.fenomeno}
          onChange={event => mudarFiltros({ fenomeno: event.target.value })}>
          {FILTROS_DE_FENOMENO.map(item => <option key={item.chave} value={item.chave}>{item.rotulo}</option>)}
        </select></label>
      <label className="analise-rotulo-campo">Porte (médicos no último registro)
        <select data-testid="detector-filtro-porte" className="analise-campo" value={filtros.porte} onChange={event => mudarFiltros({ porte: event.target.value })}>
          <option value="todos">Todos os portes</option>
          <option value="zero">Nenhum médico</option>
          {ROTULOS_DOS_PORTES.map((rotulo, indice) => <option key={rotulo} value={String(indice)}>{rotulo}</option>)}
        </select></label>
      <label className="analise-rotulo-campo">Ordem
        <select data-testid="detector-ordem" className="analise-campo" value={ordem} onChange={event => { setOrdem(event.target.value as OrdemDoDetector); setPagina(0); }}>
          <option value="intensidade">Por intensidade</option>
          <option value="nome">Por nome</option>
          <option value="medicos">Por número de médicos</option>
        </select></label>
      <label className="analise-rotulo-campo">Buscar território
        <input type="search" data-testid="detector-busca" className="analise-campo" value={filtros.busca} autoComplete="off"
          onChange={event => mudarFiltros({ busca: event.target.value })}/></label>
    </div>
    <div className="ferramenta-acoes analise-nao-imprimir">
      <button type="button" data-testid="detector-parametros-botao" className="analise-botao-secundario" aria-expanded={verParametros}
        disabled={!resposta} onClick={() => setVerParametros(valor => !valor)}><SlidersHorizontal size={14} aria-hidden="true"/>Parâmetros</button>
      <button type="button" data-testid="detector-exportar-csv" className="analise-botao-secundario" disabled={!resposta || !filtradas.length}
        onClick={() => resposta && baixar("detector_de_sinais_" + resposta.janela.fim + ".csv", csvDoDetector(resposta, filtradas), "text/csv;charset=utf-8")}>
        <Download size={14} aria-hidden="true"/>Exportar a tabela (CSV)</button>
      <button type="button" data-testid="detector-exportar-metodo" className="analise-botao-secundario" disabled={!resposta}
        onClick={() => resposta && baixar("detector_de_sinais_metodo_" + resposta.janela.fim + ".json", metodoDoDetector(resposta), "application/json")}>
        <Download size={14} aria-hidden="true"/>Exportar o método (JSON)</button>
      <span className="ferramenta-apoio">Territórios: {p.resumoDaSelecao}{" "}
        <button type="button" data-testid="detector-alterar-selecao" className="analise-link" onClick={p.onAlterarSelecao}>Alterar a seleção</button></span>
    </div>

    {resposta?.exploratorio && <p data-testid="detector-exploratorio" role="status" className="ferramenta-exploratorio">
      <strong>Configuração personalizada — exploratória.</strong> Os limites em uso são diferentes dos padrões, e estes resultados não substituem os da
      configuração padrão.{" "}
      <button type="button" data-testid="detector-padroes" className="analise-link" onClick={() => { setParametros(null); setRascunho({}); }}>Voltar aos padrões</button></p>}

    {verParametros && resposta && <form data-testid="detector-parametros" className="ferramenta-parametros" aria-label="Parâmetros exploratórios"
      onSubmit={event => { event.preventDefault(); aplicarParametros(); }}>
      <p className="ferramenta-apoio">Os padrões são limites provisórios. Trocar um valor cria uma configuração personalizada, exibida como exploratória; os
        padrões continuam disponíveis.</p>
      {Object.entries(resposta.parametros.editaveis).map(([grupo, campos]) => <fieldset key={grupo} className="ferramenta-parametros-grupo">
        <legend>{NOMES_DOS_PARAMETROS[grupo]?.grupo ?? grupo}</legend>
        {Object.entries(campos).map(([campo, faixa]) => {
          const padrao = resposta.parametros.padrao[grupo]?.[campo], emUso = resposta.parametros.emUso[grupo]?.[campo];
          return <label key={campo} className="analise-rotulo-campo">{NOMES_DOS_PARAMETROS[grupo]?.campos[campo] ?? campo}
            <input data-testid={"detector-parametro-" + grupo + "-" + campo} inputMode="decimal" className="analise-campo"
              value={rascunho[grupo]?.[campo] ?? String(emUso ?? "").replace(".", ",")}
              onChange={event => setRascunho(atual => ({ ...atual, [grupo]: { ...atual[grupo], [campo]: event.target.value } }))}/>
            <span className="ferramenta-apoio">padrão: {String(padrao ?? "").replace(".", ",")} · de {String(faixa.minimo).replace(".", ",")} a{" "}
              {String(faixa.maximo).replace(".", ",")}</span></label>;
        })}
      </fieldset>)}
      <div className="ferramenta-detalhe-acoes">
        <button type="submit" data-testid="detector-parametros-aplicar" className="analise-botao-primario">Aplicar como exploratório</button>
        <button type="button" className="analise-botao-secundario" onClick={() => { setParametros(null); setRascunho({}); }}>Voltar aos padrões</button>
      </div>
    </form>}

    {erro && <p data-testid="detector-erro" role="alert" className="analise-motivo">{erro}{" "}
      <button type="button" className="analise-link" onClick={() => setTentativa(valor => valor + 1)}>Tentar de novo</button></p>}
    {carregando && !resposta && <p role="status" className="analise-vazio"><LoaderCircle size={18} className="animate-spin" aria-hidden="true"/>Calculando os sinais…</p>}

    {resposta && resumo && <p data-testid="detector-resumo" className="ferramenta-resumo" role="status">
      <span className="ferramenta-contagem"><strong className="tabular-nums">{formatarInteiro(resumo.territorios)}</strong>{" "}
        {resumo.territorios === 1 ? "território" : "territórios"}</span>
      {contagem("com poucos médicos (escala estrutural)", resumo.sinais.estrutural, "detector-resumo-estrutural")}
      {contagem("sem médicos registrados", resumo.sinais.ausencia, "detector-resumo-ausencia")}
      {contagem("com perda no último registro", resumo.sinais.perda, "detector-resumo-perda")}
      {contagem("com alerta de perda", resumo.sinais.alerta_perda, "detector-resumo-alerta")}
      {contagem("abaixo do patamar anterior", resumo.sinais.patamar, "detector-resumo-patamar")}
      {contagem("em declínio em junhos seguidos", resumo.sinais.declinio, "detector-resumo-declinio")}
      {contagem("com desaceleração do crescimento", resumo.sinais.desaceleracao, "detector-resumo-desaceleracao")}
      {contagem("com registro a verificar", resumo.sinais.registro, "detector-resumo-registro")}
      {contagem("com queda da taxa por habitante", resumo.sinais.disponibilidade, "detector-resumo-disponibilidade")}
      {contagem("com queda de posição", resumo.sinais.posicao, "detector-resumo-posicao")}
      {contagem("com defasagem maior ante a referência", resumo.sinais.defasagem, "detector-resumo-defasagem")}
      {contagem("com sinais combinados", resumo.sinais.combinados, "detector-resumo-combinados")}
    </p>}

    {resposta && <div data-testid="detector-visual" data-vista={vista} className="ferramenta-visual">
      <div role="group" aria-label="Gráfico, mapa ou só a tabela" className="ferramenta-modos analise-nao-imprimir">
        <button type="button" data-testid="detector-vista-bolhas" className="analise-botao-secundario" aria-pressed={vista === "bolhas"}
          onClick={() => setVista("bolhas")}><ChartScatter size={14} aria-hidden="true"/>Distância e taxa (bolhas)</button>
        <button type="button" data-testid="detector-vista-mapa" className="analise-botao-secundario" aria-pressed={vista === "mapa"}
          onClick={() => setVista("mapa")}><IconeDoMapa size={14} aria-hidden="true"/>Mapa dos sinais</button>
        <button type="button" data-testid="detector-vista-tabela" className="analise-botao-secundario" aria-pressed={vista === "tabela"}
          onClick={() => setVista("tabela")}><Table size={14} aria-hidden="true"/>Só a tabela</button>
      </div>
      <p data-testid="detector-comparacao" data-estado={resposta.comparacao.estado} role="note" className="ferramenta-apoio">
        <strong>Comparação relativa</strong> (taxa por habitante, posição e defasagem ante a referência):{" "}
        {resposta.comparacao.estado === "comparavel"
          ? "variação de " + competenciaCurta(resposta.comparacao.de) + " a " + competenciaCurta(resposta.comparacao.ate) + ", em 2 anos, com população comparável."
          : resposta.comparacao.estado === "comparacao_nao_habilitada"
            ? "a variação de " + competenciaCurta(resposta.comparacao.de) + " a " + competenciaCurta(resposta.comparacao.ate) + " não é calculada (comparação não " +
              "habilitada): a população de 2021 a 2023 é repetida, e a de 2024 é de outra base. A taxa, a posição e o índice da data continuam à vista. Para " +
              "ver a variação, termine a janela entre jun/2016 e jan/2018 ou entre jun/2020 e jan/2022."
            : "a variação não é calculada nesta janela: falta o registro de junho de dois anos antes."}{" "}
        <strong>Contexto geográfico:</strong>{" "}
        {resposta.comparacao.contexto.taxaMinima === null ? "sem a taxa do Brasil na data, o critério não pode ser aplicado."
          : "distância em linha reta até o município mais próximo com " + formatarTaxa(resposta.comparacao.contexto.taxaMinima) + " médicos por 1.000 " +
            "habitantes ou mais (" + formatarInteiro(Math.round(resposta.comparacao.contexto.pctDaTaxaDoBrasil ?? 100)) + "% da taxa do Brasil em " +
            competenciaCurta(resposta.janela.fim) + "); " + formatarInteiro(resposta.comparacao.contexto.atendem) + " municípios do país atendem ao critério."}
      </p>
      {vista === "bolhas" && <BolhasDoContexto resposta={resposta} linhas={filtradas} onAbrir={abrirDoDesenho}/>}
      {vista === "mapa" && <MapaDosSinais resposta={resposta} linhas={filtradas} fenomeno={filtros.fenomeno} onAbrir={abrirDoDesenho}/>}
    </div>}

    {resposta && <div className="ferramenta-rolagem">
      <table data-testid="detector-tabela" data-linhas={filtradas.length} className="analise-tabela ferramenta-tabela">
        <caption className="ferramenta-apoio">Detalhes por território. {TEXTO_LIMITES_PROVISORIOS} Situação em {competenciaCurta(resposta.janela.fim)}; janela desde{" "}
          {competenciaCurta(resposta.janela.inicio)}. {TEXTO_SINAIS_RELATIVOS} O contexto geográfico e os sinais combinados também não têm intensidade.</caption>
        <thead><tr>
          <th scope="col">Território</th><th scope="col">Condição estrutural</th><th scope="col">Trajetória</th>
          <th scope="col">Ritmo e instabilidade</th><th scope="col">Comparação relativa</th><th scope="col">Contexto geográfico</th>
          <th scope="col">Sinais combinados</th><th scope="col">Qualidade do registro</th><th scope="col">Última observação</th>
        </tr></thead>
        <tbody>
          {naPagina.map(linha => {
            const registro = textoDoRegistro(linha), trajetoria = trechosDaTrajetoria(linha), ritmo = trechosDoRitmo(linha), tipo = tipoDoTerritorio(linha);
            const comparacao = trechosDaComparacao(linha), combinados = trechosCombinados(linha);
            const detalhe = detalhes[linha.id], expandida = aberto === linha.id;
            return <Fragment key={linha.id}>
              <tr data-testid="detector-linha" data-id={linha.id} data-tipo={linha.tipo} data-sinais={linha.sinais.join(" ")}
                data-estrutural={linha.dimensoes.estrutural ?? ""} data-trajetoria={linha.dimensoes.trajetoria ?? ""}>
                <th scope="row" className="ferramenta-territorio">
                  <button type="button" data-testid="detector-abrir" className="ferramenta-abrir" aria-expanded={expandida}
                    aria-label={(expandida ? "Fechar os detalhes de " : "Ver os detalhes de ") + linha.rotulo}
                    onClick={() => setAberto(atual => atual === linha.id ? null : linha.id)}>
                    {expandida ? <ChevronDown size={15} aria-hidden="true"/> : <ChevronRight size={15} aria-hidden="true"/>}
                    <span>{linha.rotulo}</span></button>
                  {tipo && <span className="ferramenta-apoio">{tipo}</span>}
                </th>
                <td><TrechoDaLinha trecho={trechoEstrutural(linha)}/></td>
                <td>{trajetoria.length ? trajetoria.map(trecho => <TrechoDaLinha key={trecho.chave} trecho={trecho}/>)
                  : <span className="ferramenta-apoio">{linha.perda.estado === "ausencia_de_dado" ? "sem registro nesta data" : "sem perda no último registro"}</span>}</td>
                <td>{ritmo.length ? ritmo.map(trecho => <TrechoDaLinha key={trecho.chave} trecho={trecho}/>) : <span className="ferramenta-apoio">—</span>}</td>
                <td className="ferramenta-coluna-larga">{comparacao.length ? comparacao.map(trecho => <TrechoDaLinha key={trecho.chave} trecho={trecho}/>)
                  : <span className="ferramenta-apoio">{linha.posicao.estado === "nao_aplicavel" && linha.disponibilidade.taxa === null
                    ? "sem taxa por habitante neste território" : "sem taxa por habitante nesta data"}</span>}</td>
                <td><TrechoDaLinha trecho={trechoDoContexto(linha)}/></td>
                <td>{combinados.length ? combinados.map((trecho, indice) => <TrechoDaLinha key={indice} trecho={trecho}/>)
                  : <span className="ferramenta-apoio">—</span>}</td>
                <td><span data-testid="detector-registro" data-marca={registro.marca} className={"ferramenta-registro ferramenta-registro-" + registro.marca}>
                  {registro.texto}</span></td>
                <td>{textoDaUltima(linha, resposta.janela.fim)}</td>
              </tr>
              {expandida && <tr className="ferramenta-linha-detalhe"><td colSpan={9}>
                {!detalhe ? <p role="status" className="ferramenta-apoio"><LoaderCircle size={14} className="animate-spin inline" aria-hidden="true"/> Abrindo os detalhes…</p>
                  : "erro" in detalhe ? <p role="alert" className="analise-motivo">{detalhe.erro}</p>
                    : <DetalheDoTerritorio detalhe={detalhe} patamar={patamarARecuperar(linha)} onAbrirNoSimulador={p.onAbrirNoSimulador
                      ? () => p.onAbrirNoSimulador!(alvoDoSimulador(linha, resposta)) : undefined}
                      onSimularRecuperacao={p.onSimularRecuperacao && patamarARecuperar(linha) !== null
                        ? () => p.onSimularRecuperacao!(alvoDoSimulador(linha, resposta), patamarARecuperar(linha)!) : undefined}/>}
              </td></tr>}
            </Fragment>;
          })}
          {!filtradas.length && <tr><td colSpan={9} data-testid="detector-sem-linhas" className="ferramenta-apoio">Nenhum território da seleção passa nos filtros.</td></tr>}
        </tbody>
      </table>
    </div>}
    {resposta && paginas > 1 && <nav data-testid="detector-paginas" className="ferramenta-paginas analise-nao-imprimir" aria-label="Páginas da tabela">
      <button type="button" className="analise-botao-secundario" disabled={paginaAtual === 0} onClick={() => setPagina(paginaAtual - 1)}>Anterior</button>
      <span className="ferramenta-apoio">Página {paginaAtual + 1} de {paginas} · {formatarInteiro(filtradas.length)} territórios</span>
      <button type="button" className="analise-botao-secundario" disabled={paginaAtual >= paginas - 1} onClick={() => setPagina(paginaAtual + 1)}>Próxima</button>
    </nav>}

    {resposta && <div className="ferramenta-metodo">
      <button type="button" data-testid="detector-metodo-botao" className="analise-link" aria-expanded={verMetodo}
        onClick={() => setVerMetodo(valor => !valor)}>{verMetodo ? "Fechar “Como foi calculado”" : "Como foi calculado"}</button>
      {verMetodo && <div data-testid="detector-metodo" className="ferramenta-metodo-corpo">
        <ul className="ferramenta-notas">{resposta.notas.map(nota => <li key={nota}>{nota}</li>)}</ul>
        {resposta.calibracao.perda.length > 0 && <div className="ferramenta-rolagem"><table data-testid="detector-calibracao" className="analise-tabela ferramenta-tabela">
          <caption className="ferramenta-apoio">Perda entre dois registros em {competenciaCurta(resposta.calibracao.competencia)} (intervalo de{" "}
            {resposta.calibracao.intervaloMeses} meses): a partir de que queda a variação é incomum, só com as transições anteriores de municípios do mesmo
            porte (excepcionalidade calibrada por porte e intervalo; limites provisórios de 1% e 0,1%).</caption>
          <thead><tr><th scope="col">Médicos antes</th><th scope="col">Transições anteriores</th><th scope="col">Queda incomum a partir de</th>
            <th scope="col">Queda muito incomum a partir de</th></tr></thead>
          <tbody>{resposta.calibracao.perda.map(celula => <tr key={celula.porte}>
            <th scope="row">{celula.porte}</th><td>{formatarInteiro(celula.transicoes)}</td>
            <td>{celula.quedaIncomumPct === null ? (celula.alta === "sem_calibracao" ? "sem classificação: poucas transições" : "nenhuma queda tão rara")
              : formatarPct(celula.quedaIncomumPct)}</td>
            <td>{celula.quedaMuitoIncomumPct === null ? (celula.critica === "sem_calibracao" ? "sem classificação: poucas transições" : "nenhuma queda tão rara")
              : formatarPct(celula.quedaMuitoIncomumPct)}</td></tr>)}</tbody>
        </table></div>}
        {resposta.calibracao.patamar.length > 0 && <div className="ferramenta-rolagem"><table className="analise-tabela ferramenta-tabela">
          <caption className="ferramenta-apoio">Afastamento do patamar anterior: a partir de quanto ele é incomum, por faixa do patamar (a intensidade crítica não
            é calibrável na base atual).</caption>
          <thead><tr><th scope="col">Patamar (médicos)</th><th scope="col">Avaliações anteriores</th><th scope="col">Afastamento incomum a partir de</th></tr></thead>
          <tbody>{resposta.calibracao.patamar.map(faixa => <tr key={faixa.porte}><th scope="row">{faixa.porte}</th>
            <td>{formatarInteiro(faixa.observacoes)}</td>
            <td>{faixa.afastamentoIncomumPct === null ? "sem classificação" : formatarPct(faixa.afastamentoIncomumPct)}</td></tr>)}</tbody>
        </table></div>}
        <p className="ferramenta-apoio">Método {resposta.versao} · base {resposta.fonte.base} ({resposta.fonte.categoria.toLowerCase()}), versão{" "}
          {resposta.fonte.versao.slice(0, 12)} · monitoramento: {formatarInteiro(resposta.calibracao.monitoramento.incomuns)} de{" "}
          {formatarInteiro(resposta.calibracao.monitoramento.avaliadas)} transições municipais na cauda de 1% nesta data.</p>
      </div>}
    </div>}
  </section>;
}
