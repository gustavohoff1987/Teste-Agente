import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownUp, ChartScatter, ChevronDown, ChevronRight, Download, List, LoaderCircle, Map as IconeDoMapa, RotateCcw, SlidersHorizontal } from "lucide-react";
import { BolhasDoContexto, MapaDosNiveis, SerieDaTaxa } from "./DetectorGraficos";
import Entenda from "./Entenda";
import { ErroDoMotor, pedirAoMotor, type FonteDoMotor } from "./painelApi";
import {
  ESTADOS_DO_ALERTA, NIVEIS, NOMES_DOS_NIVEIS, SEM_FILTROS, alvoDoSimulador, competenciaCurta, criteriosEmFrases, csvDoDetector, estadoDoAlerta,
  filtrarLinhas, filtrosDeSinal, formatarInteiro, formatarPct, formatarTaxa, metodoDoDetector, nomeDoEstado, nomeDoSinal, normalizarDetalhe,
  normalizarDetector, ordenarLinhas, parametrosPersonalizados, patamarARecuperar, profissionais, rotuloDoCampo, textoDaContagem, textoDaMesmaQueda,
  textoDaUltima, textoDoAlerta, textoDoCorte, textoDoPorQue, textoDoRegistro, textoDosTrechos, tipoDoTerritorio,
  type AlvoDoSimulador, type DetalheDoDetector, type EstadoDoAlerta, type FaixaDaRegua, type FenomenoDoDetalhe, type FiltrosDoDetector,
  type LinhaDoDetector, type NivelDoAlerta, type OpcoesDoDetector, type OrdemDoDetector, type ParametrosDoDetector, type ReguaDaData,
  type RespostaDoDetector, type RotulosDaBase, type SelecaoDasFerramentas,
} from "./detectorModel";

// Detector de Sinais Territoriais (comando V23, Proposta V3, Parte B; Docs/DETECTOR_DE_SINAIS.md). A primeira tela é uma lista de
// quatro colunas (Território · Alerta · Por quê · Último registro), com o resumo dos níveis no alto, clicável como filtro, os
// filtros numa linha (Até, Nível, Sinal e Buscar) e as visões Lista, Mapa e Gráfico. Cada território tem um nível só — moderado,
// elevado ou crítico, o maior entre os seus sinais, sem soma nem índice —, sempre escrito e com o tipo de critério ("comparado
// com a base" ou "por convenção"); quando a base não tem comparações bastantes, a tela diz "sem comparações suficientes", com
// os números. "Ajustar critérios" mostra os limites em frases, com os campos dentro delas: trocar um valor torna a configuração
// exploratória, com aviso no alto, e "Voltar ao padrão" fica sempre à vista. O detalhe de um território traz a série e os 12
// sinais em quatro grupos (Quantos há, Como mudou, Comparado com outros, Onde fica), mais Juntos; em cada sinal, o nível, uma
// frase e o "Entenda" (Entenda.tsx), com a explicação inteira em "Ver explicação completa". Todo número e todo texto de resultado
// vêm do motor (POST /api/detector), que calcula sem o provedor de IA. A tela só filtra, ordena e desenha.

const POR_PAGINA = 50;
type Props = {
  fonte: FonteDoMotor;
  /** A seleção em uso (a da Seleção de Territórios); null sem territórios. */
  selecao: SelecaoDasFerramentas | null;
  resumoDaSelecao: string;
  onAlterarSelecao: () => void;
  /** Abre o território no Simulador de Cenários, com o contexto analítico (a data avaliada, a janela escolhida e os sinais com nível). */
  onAbrirNoSimulador?: (alvo: AlvoDoSimulador) => void;
  /** "Simular recuperação": abre o Simulador com o território e, como meta hipotética e editável, o patamar do sinal 7. */
  onSimularRecuperacao?: (alvo: AlvoDoSimulador, patamar: number) => void;
};
type Vista = "lista" | "mapa" | "grafico";

function baixar(nome: string, corpo: string, tipo: string) {
  const url = URL.createObjectURL(new Blob([corpo], { type: tipo }));
  const link = document.createElement("a");
  link.href = url; link.download = nome; link.click();
  URL.revokeObjectURL(url);
}

/** O nível, com o nome por extenso (nunca só a cor). */
function Nivel({ nivel }: { nivel: NivelDoAlerta }) {
  return <span data-testid="detector-nivel" data-nivel={nivel} className={"ferramenta-nivel ferramenta-nivel-" + nivel}>{NOMES_DOS_NIVEIS[nivel]}</span>;
}

/** A série observada de um território: só os registros reais, com as marcas de registro. Sem linha ajustada. */
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
  // As datas escritas no eixo: as do mês do último registro (o mês âncora da série anual), um ano sim, outro não, e a última.
  const mes = pontos[pontos.length - 1].competencia.slice(4);
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
      {pontos.map((ponto, indice) => ponto.competencia.endsWith(mes) && (indice === pontos.length - 1 || Number(ponto.competencia.slice(0, 4)) % 2 === 0)
        ? <text key={"a" + ponto.competencia} x={x(indice)} y={altura - 12} textAnchor="middle" className="ferramenta-serie-texto">
          {competenciaCurta(ponto.competencia)}</text> : null)}
    </svg>
    <figcaption className="ferramenta-apoio">Registros observados. Pontos maiores: registro com marca (pico que volta, quebra de fonte ou
      “verificar registro”). ×: sem registro. Nenhuma linha é ajustada, e nada é estimado entre os registros.</figcaption>
  </figure>;
}

const CAMPOS_DA_EXPLICACAO: [keyof FenomenoDoDetalhe, string][] = [
  ["observado", "O que foi observado"], ["criterio", "Qual critério"], ["habitual", "Comparado com o comum"], ["significa", "O que significa"],
  ["naoSignifica", "O que não significa"], ["limitacoes", "Limitações do dado"], ["qualidade", "Qualidade do registro"]];
const ESTADOS_DO_NIVEL: Record<string, string> = { sem_alerta: "Sem alerta", sem_comparacoes: "Sem comparações suficientes", sem_nivel: "Sem nível (conjunto)",
  sem_dado: "Sem dado para avaliar", nao_avaliado: "Não avaliado", contexto: "Só contexto", juntos: "" };

/** Um sinal no detalhe: o nível (com o tipo de critério), uma frase, o "Entenda" e, quando pedida, a explicação completa. */
function SinalDoTerritorio({ sinal, aberto, onAlternar }: { sinal: FenomenoDoDetalhe; aberto: boolean; onAlternar: (abrir?: boolean) => void }) {
  const estado = sinal.nivel ? null : ESTADOS_DO_NIVEL[sinal.estadoDoNivel] ?? "Sem alerta";
  return <li data-testid="detector-fenomeno" data-chave={sinal.chave} data-nivel={sinal.nivel ?? ""} data-estado={sinal.estadoDoNivel}
    className="ferramenta-fenomeno">
    <div className="ferramenta-sinal">
      <span className="ferramenta-sinal-nome"><span className="ferramenta-apoio">Sinal {sinal.numero}</span>{sinal.nome}</span>
      <span data-testid="detector-fenomeno-nivel" className="ferramenta-sinal-nivel">
        {sinal.nivel ? <><Nivel nivel={sinal.nivel}/><span data-testid="detector-fenomeno-criterio" className="ferramenta-apoio">
          {sinal.criterioDoNivel}{sinal.exploratorio ? " · exploratório" : ""}</span></>
          : estado ? <span className="ferramenta-sem-nivel">{estado}</span> : null}
      </span>
      <span data-testid="detector-fenomeno-situacao" className="ferramenta-sinal-frase">{sinal.situacao}
        {sinal.semComparacoes && <span data-testid="detector-fenomeno-sem-comparacoes" className="ferramenta-apoio ferramenta-sinal-falta">
          {sinal.semComparacoes.texto}</span>}</span>
      <span className="ferramenta-sinal-acoes">
        <Entenda sobre={sinal.nome} texto={sinal.entenda.texto} exemplo={sinal.entenda.exemplo} testid="detector-entenda" onCompleta={() => onAlternar(true)}/>
        <button type="button" data-testid="detector-fenomeno-completa" className="analise-link" aria-expanded={aberto} onClick={() => onAlternar()}>
          {aberto ? "Fechar a explicação" : "Explicação completa"}</button>
      </span>
    </div>
    {aberto && <dl data-testid="detector-fenomeno-explicacao" className="ferramenta-fenomeno-corpo">
      {CAMPOS_DA_EXPLICACAO.map(([campo, rotulo]) => <div key={campo} data-testid={"detector-campo-" + campo}>
        <dt>{rotulo}</dt><dd>{String(sinal[campo])}</dd></div>)}
    </dl>}
  </li>;
}

function DetalheDoTerritorio({ detalhe, linha, resposta, patamar, onAbrirNoSimulador, onSimularRecuperacao }: { detalhe: DetalheDoDetector;
  linha: LinhaDoDetector; resposta: RespostaDoDetector;
  /** O patamar do território (sinal 7), quando ele está abaixo dele: a meta hipotética de "Simular recuperação". */
  patamar: number | null; onAbrirNoSimulador?: () => void; onSimularRecuperacao?: () => void }) {
  const r = resposta.fonte.rotulos;
  const [abertos, setAbertos] = useState<string[]>([]);
  const [verHistorico, setVerHistorico] = useState(false);
  const alternar = (chave: string, abrir?: boolean) => setAbertos(atual => abrir === true ? [...new Set([...atual, chave])]
    : atual.includes(chave) ? atual.filter(item => item !== chave) : [...atual, chave]);
  const alerta = textoDoAlerta(linha), mesmaQueda = textoDaMesmaQueda(linha, r);
  return <div data-testid="detector-detalhe" data-id={detalhe.id} className="ferramenta-detalhe">
    <p data-testid="detector-detalhe-alerta" data-estado={alerta.estado} className="ferramenta-detalhe-alerta">
      {alerta.nivel ? <><Nivel nivel={alerta.nivel}/><span className="ferramenta-apoio">{alerta.criterio}</span></>
        : <span className="ferramenta-sem-nivel">{alerta.texto}</span>}
      <span>{textoDoPorQue(linha, r)}</span>
      {mesmaQueda && <span data-testid="detector-mesma-queda" className="ferramenta-apoio">{mesmaQueda}</span>}
    </p>
    <p className="ferramenta-apoio">Contagem: {detalhe.unidade}.{detalhe.membros.length > 0 && " Componentes: " + detalhe.membros.join(", ") + "."}
      {detalhe.depoisDaQuebra && " Os indicadores deste território começam em " + competenciaCurta(detalhe.inicioDoTerritorio) + ", depois da quebra de fonte."}</p>
    <SerieObservada detalhe={detalhe}/>
    <SerieDaTaxa detalhe={detalhe} profissionais={r.profissionais}/>
    {resposta.grupos.map(grupo => {
      const sinais = detalhe.fenomenos.filter(sinal => sinal.grupo === grupo.chave);
      return sinais.length ? <section key={grupo.chave} data-testid="detector-grupo" data-grupo={grupo.chave} className="ferramenta-grupo"
        aria-label={grupo.nome + ": sinais de " + detalhe.rotulo}>
        <h4 className="ferramenta-grupo-titulo">{grupo.nome}</h4>
        <ul className="ferramenta-fenomenos">{sinais.map(sinal => <SinalDoTerritorio key={sinal.chave} sinal={sinal}
          aberto={abertos.includes(sinal.chave)} onAlternar={abrir => alternar(sinal.chave, abrir)}/>)}</ul>
      </section> : null;
    })}
    <div className="ferramenta-detalhe-acoes">
      <button type="button" data-testid="detector-historico-botao" className="analise-botao-secundario" aria-expanded={verHistorico}
        onClick={() => setVerHistorico(valor => !valor)}>{verHistorico ? "Fechar o histórico de sinais" : "Ver o histórico de sinais"}</button>
      {onAbrirNoSimulador && <button type="button" data-testid="detector-abrir-no-simulador" className="analise-botao-secundario"
        title="Leva este território ao Simulador de Cenários, com a data avaliada, a janela escolhida e os sinais com nível" onClick={onAbrirNoSimulador}>
        Abrir no Simulador</button>}
      {onSimularRecuperacao && patamar !== null && <button type="button" data-testid="detector-simular-recuperacao" className="analise-botao-secundario"
        title={"Abre o Simulador com a meta hipotética de voltar ao patamar de " + formatarTaxa(patamar).replace(/,00$/, "") + " " + r.profissionais +
          "; a meta pode ser trocada"} onClick={onSimularRecuperacao}>Simular recuperação</button>}
    </div>
    {onSimularRecuperacao && patamar !== null && <p data-testid="detector-recuperacao-apoio" className="ferramenta-apoio">“Simular recuperação” abre o
      Simulador de Cenários com uma meta hipotética: voltar ao patamar de {profissionais(Math.round(patamar), r)} (a maior média de dois anos seguidos antes
      dos registros mais recentes). A meta é uma hipótese que você pode trocar; o resultado é um cenário, não uma previsão.</p>}
    {verHistorico && <div className="ferramenta-rolagem"><table data-testid="detector-historico" className="analise-tabela ferramenta-tabela">
      <caption className="ferramenta-apoio">Histórico de sinais na janela (sinais 1 a 7): cada data avaliada só com o que era conhecido nela.</caption>
      <thead><tr><th scope="col">Registro</th><th scope="col">Número</th><th scope="col">Alerta</th><th scope="col">{nomeDoSinal("estrutural", r)}</th>
        <th scope="col">Queda desde o registro anterior</th><th scope="col">Ante o patamar</th><th scope="col">Série anual</th></tr></thead>
      <tbody>{detalhe.historico.map(passo => <tr key={passo.competencia} data-competencia={passo.competencia} data-alerta={passo.alerta ?? ""}>
        <th scope="row">{competenciaCurta(passo.competencia)}</th>
        <td>{passo.valor === null ? "sem registro" : formatarInteiro(passo.valor)}</td>
        <td>{passo.alerta ? <Nivel nivel={passo.alerta}/> : "—"}</td>
        <td>{passo.estrutural ? <Nivel nivel={passo.estrutural}/> : "—"}</td>
        <td>{passo.perda ? <>{"−" + formatarInteiro(Math.abs(passo.perda.delta)) + (passo.perda.pct !== null ? " (−" + formatarPct(passo.perda.pct) + ")" : "")}{" "}
          {passo.perda.classe ? <Nivel nivel={passo.perda.classe}/> : <span className="ferramenta-apoio">
            {passo.perda.estado === "descontinuidade_de_registro" ? "descontinuidade de registro" : passo.perda.estado === "sem_comparacoes"
              ? "sem comparações suficientes" : "sem alerta"}</span>}</> : "—"}</td>
        <td>{passo.patamar.diferencaPct === null ? "—" : <>{formatarPct(passo.patamar.diferencaPct) + (passo.patamar.diferencaPct < 0 ? " abaixo" : " acima")}{" "}
          {passo.patamar.classe && <Nivel nivel={passo.patamar.classe}/>}</>}</td>
        <td>{passo.declinio === null ? "" : <>{[(passo.declinio.reducoes ?? 0) >= 2 ? passo.declinio.reducoes + " quedas anuais seguidas" : "",
          passo.desaceleracao?.desacelera ? "crescimento perde ritmo" : ""].filter(Boolean).join(" · ") || "—"}{" "}
          {passo.declinio.classe && <Nivel nivel={passo.declinio.classe}/>}</>}</td>
      </tr>)}</tbody>
    </table></div>}
  </div>;
}

/** A régua da data, por faixa de porte: quantas comparações há e a partir de que mudança ela é rara em cada nível. */
function TabelaDaRegua({ regua, faixas, titulo, o_que, testid, r }: { regua: ReguaDaData; faixas: FaixaDaRegua[]; titulo: string; o_que: string;
  testid: string; r: RotulosDaBase }) {
  const niveis = [...NIVEIS].reverse().filter(nivel => faixas.some(faixa => faixa.niveis[nivel]));
  if (!faixas.length) return null;
  return <div className="ferramenta-rolagem"><table data-testid={testid} className="analise-tabela ferramenta-tabela">
    <caption className="ferramenta-apoio">{titulo} Régua de {competenciaCurta(regua.competencia)}{regua.intervaloMeses ? ", com as mudanças anteriores de " +
      regua.intervaloMeses + " meses entre registros" : ""}: só o que veio antes da data.</caption>
    <thead><tr><th scope="col">Porte ({r.profissionais})</th><th scope="col">Comparações anteriores</th>
      {niveis.map(nivel => <th key={nivel} scope="col">{NOMES_DOS_NIVEIS[nivel]} (1 em cada {formatarInteiro(faixas[0].niveis[nivel]?.umEm ?? 0)})</th>)}</tr></thead>
    <tbody>{faixas.map(faixa => <tr key={faixa.porte} data-porte={faixa.porte}>
      <th scope="row">{faixa.porte}</th><td>{formatarInteiro(faixa.comparacoes)}</td>
      {niveis.map(nivel => <td key={nivel} data-nivel={nivel}>{textoDoCorte(faixa, nivel, o_que)}</td>)}</tr>)}</tbody>
  </table></div>;
}

export default function DetectorDeSinais(p: Props) {
  const [janela, setJanela] = useState<{ inicio?: string; fim?: string }>({});
  const [parametros, setParametros] = useState<ParametrosDoDetector | null>(null);
  const [resposta, setResposta] = useState<RespostaDoDetector | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [tentativa, setTentativa] = useState(0);
  const [filtros, setFiltros] = useState<FiltrosDoDetector>(SEM_FILTROS);
  const [ordem, setOrdem] = useState<OrdemDoDetector>("nivel");
  const [pagina, setPagina] = useState(0);
  const [aberto, setAberto] = useState<string | null>(null);
  const [detalhes, setDetalhes] = useState<Record<string, DetalheDoDetector | { erro: string }>>({});
  const [verCriterios, setVerCriterios] = useState(false);
  const [rascunho, setRascunho] = useState<Record<string, Record<string, string>>>({});
  const [verMetodo, setVerMetodo] = useState(false);
  const [vista, setVista] = useState<Vista>("lista");
  const cache = useRef(new Map<string, RespostaDoDetector>());
  const metodo = useRef<HTMLDivElement>(null);

  const pedido: OpcoesDoDetector | null = useMemo(() => p.selecao ? { ...p.selecao, ...(janela.inicio || janela.fim ? { janela } : {}),
    ...(parametros ? { parametros } : {}) } : null, [p.selecao, janela, parametros]);
  const chave = pedido ? p.fonte.datasetVersion + "::" + JSON.stringify(pedido) : "";

  // A lista: pedida ao motor a cada mudança da seleção, da janela ou dos critérios; a resposta de um pedido igual vem da memória.
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
  const r = resposta?.fonte.rotulos;
  const mudarFiltros = (parte: Partial<FiltrosDoDetector>) => { setFiltros(atual => ({ ...atual, ...parte })); setPagina(0); };
  const voltarAoPadrao = () => { setParametros(null); setRascunho({}); };
  const comRascunho = Object.values(rascunho).some(campos => Object.keys(campos).length > 0);
  /** Abre os detalhes de um território a partir do mapa ou do gráfico: a linha dele vai para a página à vista. */
  function abrirDoDesenho(id: string) {
    const posicao = filtradas.findIndex(linha => linha.id === id);
    if (posicao < 0) return;
    setPagina(Math.floor(posicao / POR_PAGINA));
    setAberto(id);
    requestAnimationFrame(() => document.querySelector('[data-testid="detector-linha"][data-id="' + id + '"]')?.scrollIntoView({ block: "center" }));
  }
  /** "Ver explicação completa" do "Entenda" da primeira tela: abre "Como foi calculado" e leva a pessoa até lá. */
  function abrirOMetodo() {
    setVerMetodo(true);
    requestAnimationFrame(() => metodo.current?.scrollIntoView({ block: "start" }));
  }

  function aplicarCriterios() {
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
    <div className="ferramenta-titulo-linha">
      <h2 id="detector-titulo" data-testid="detector-titulo" tabIndex={-1} className="analise-titulo">Detector de Sinais Territoriais</h2>
      {resposta?.entenda.ferramenta && <Entenda sobre="Detector de Sinais" texto={resposta.entenda.ferramenta.texto}
        exemplo={resposta.entenda.ferramenta.exemplo} testid="detector-entenda-ferramenta" onCompleta={abrirOMetodo}/>}
    </div>
    <p className="analise-subtitulo">Compara cada território com o que é comum na própria base. Descreve os registros; não diz se o atendimento é
      suficiente nem onde prover.</p>
  </header>;

  if (!p.selecao) return <section data-testid="detector" data-estado="sem-selecao" aria-labelledby="detector-titulo" className="ferramenta">
    {cabecalho}
    <p data-testid="detector-sem-selecao" role="status" className="analise-motivo">Nenhum território selecionado.{" "}
      <button type="button" className="analise-link" onClick={p.onAlterarSelecao}>Selecionar os territórios</button></p>
  </section>;

  const criterios = r ? criteriosEmFrases(r) : [];
  const cabecaDeOrdem = (rotulo: string, valor: OrdemDoDetector, testid: string) => <button type="button" data-testid={testid}
    className="ferramenta-ordenar" aria-pressed={ordem === valor} title={"Ordenar por " + rotulo.toLowerCase()}
    onClick={() => { setOrdem(valor); setPagina(0); }}>{rotulo}<ArrowDownUp size={12} aria-hidden="true"/></button>;
  return <section data-testid="detector" data-estado={carregando ? "carregando" : erro ? "erro" : resposta ? "pronto" : "vazio"}
    data-exploratorio={resposta?.exploratorio ? "true" : "false"} aria-labelledby="detector-titulo" aria-busy={carregando || undefined} className="ferramenta">
    {cabecalho}
    {resposta && <p data-testid="detector-data" role="note" className="ferramenta-aviso">Registro mais recente da base: <strong>{competenciaCurta(resposta.janela.ultimoRegistroDaBase)}</strong>.
      Os sinais descrevem a situação até {competenciaCurta(resposta.janela.fim)}, não a de hoje.</p>}
    {resposta?.avisoDaBase && <p data-testid="detector-aviso-da-base" role="status" className="ferramenta-exploratorio"><strong>Aviso da base.</strong>{" "}
      {resposta.avisoDaBase}</p>}
    {resposta?.exploratorio && <p data-testid="detector-exploratorio" role="status" className="ferramenta-exploratorio">
      <strong>Configuração exploratória.</strong> Os critérios em uso são diferentes do padrão, e estes resultados não substituem os da configuração padrão.{" "}
      <button type="button" data-testid="detector-padroes" className="analise-link" onClick={voltarAoPadrao}>Voltar ao padrão</button></p>}

    <div className="ferramenta-filtros analise-nao-imprimir" role="group" aria-label="Filtros da lista">
      <label className="analise-rotulo-campo">Até
        <select data-testid="detector-janela-fim" className="analise-campo" value={fimEmUso} disabled={!competencias.length}
          onChange={event => setJanela(atual => ({ ...atual, fim: event.target.value }))}>
          {competencias.filter(c => !inicioEmUso || c >= inicioEmUso).map(c => <option key={c} value={c}>{competenciaCurta(c)}</option>)}
        </select></label>
      <label className="analise-rotulo-campo">Nível
        <select data-testid="detector-filtro-nivel" className="analise-campo" value={filtros.nivel} onChange={event => mudarFiltros({ nivel: event.target.value })}>
          <option value="todos">Todos</option>
          {ESTADOS_DO_ALERTA.map(estado => <option key={estado} value={estado}>{nomeDoEstado(estado)}</option>)}
        </select></label>
      <label className="analise-rotulo-campo">Sinal
        <select data-testid="detector-filtro-sinal" className="analise-campo" value={filtros.sinal} onChange={event => mudarFiltros({ sinal: event.target.value })}>
          {filtrosDeSinal(r).map(item => <option key={item.chave} value={item.chave}>{item.rotulo}</option>)}
        </select></label>
      <label className="analise-rotulo-campo ferramenta-filtro-busca">Buscar território
        <input type="search" data-testid="detector-busca" className="analise-campo" value={filtros.busca} autoComplete="off"
          onChange={event => mudarFiltros({ busca: event.target.value })}/></label>
      <div className="ferramenta-filtros-acoes">
        <button type="button" data-testid="detector-parametros-botao" className="analise-botao-secundario" aria-expanded={verCriterios}
          disabled={!resposta} onClick={() => setVerCriterios(valor => !valor)}><SlidersHorizontal size={14} aria-hidden="true"/>Ajustar critérios</button>
        <button type="button" data-testid="detector-voltar-ao-padrao" className="analise-botao-secundario" disabled={!resposta?.exploratorio && !comRascunho}
          title={resposta?.exploratorio || comRascunho ? "Volta aos critérios padrão" : "Os critérios em uso já são os do padrão"}
          onClick={voltarAoPadrao}><RotateCcw size={14} aria-hidden="true"/>Voltar ao padrão</button>
      </div>
    </div>

    {verCriterios && resposta && <form data-testid="detector-parametros" className="ferramenta-criterios" aria-label="Ajustar critérios"
      onSubmit={event => { event.preventDefault(); aplicarCriterios(); }}>
      <p className="ferramenta-apoio">Os limites de cada sinal, em frases. Troque um valor dentro da frase e aplique: a configuração passa a ser{" "}
        <strong>exploratória</strong>, com aviso no alto, nos textos e nas exportações. O padrão continua disponível em “Voltar ao padrão”.</p>
      <label className="analise-rotulo-campo ferramenta-criterio-janela">Considerar os registros desde
        <select data-testid="detector-janela-inicio" className="analise-campo" value={inicioEmUso} disabled={!competencias.length}
          onChange={event => setJanela(atual => ({ ...atual, inicio: event.target.value }))}>
          {competencias.filter(c => !fimEmUso || c <= fimEmUso).map(c => <option key={c} value={c}>{competenciaCurta(c)}</option>)}
        </select></label>
      {criterios.map(criterio => <fieldset key={criterio.sinal} data-testid="detector-criterio" data-sinal={criterio.sinal} className="ferramenta-criterio">
        <legend><span className="ferramenta-apoio">Sinal {criterio.numero}</span> {criterio.titulo} <span className="ferramenta-apoio">· {criterio.tipo}</span></legend>
        {criterio.frases.map((frase, indiceDaFrase) => <p key={indiceDaFrase} className="ferramenta-frase">
          {frase.map((parte, indice) => {
            if (typeof parte === "string") return <Fragment key={indice}>{parte}</Fragment>;
            const faixa = resposta.parametros.editaveis[parte.grupo]?.[parte.campo];
            const padrao = resposta.parametros.padrao[parte.grupo]?.[parte.campo], emUso = resposta.parametros.emUso[parte.grupo]?.[parte.campo];
            const valor = rascunho[parte.grupo]?.[parte.campo] ?? String(emUso ?? "").replace(".", ",");
            const trocado = Number(valor.replace(",", ".")) !== padrao;
            return <input key={indice} data-testid={"detector-parametro-" + parte.grupo + "-" + parte.campo} data-trocado={trocado ? "true" : "false"}
              inputMode="decimal" className={"ferramenta-campo-da-frase" + (trocado ? " ferramenta-campo-trocado" : "")}
              aria-label={rotuloDoCampo(criterio, frase, indice)} size={Math.max(2, valor.length)} value={valor}
              title={"padrão: " + String(padrao ?? "").replace(".", ",") + (faixa ? " · de " + String(faixa.minimo).replace(".", ",") + " a " +
                String(faixa.maximo).replace(".", ",") : "")}
              onChange={event => setRascunho(atual => ({ ...atual, [parte.grupo]: { ...atual[parte.grupo], [parte.campo]: event.target.value } }))}/>;
          })}
        </p>)}
      </fieldset>)}
      <p className="ferramenta-apoio">Sinal 12 (sinais juntos): mostra quais sinais com nível coincidem no território e não tem limite a ajustar. Passe o
        mouse num campo para ver o padrão e o intervalo aceito.</p>
      <div className="ferramenta-detalhe-acoes">
        <button type="submit" data-testid="detector-parametros-aplicar" className="analise-botao-primario">Aplicar como configuração exploratória</button>
        <button type="button" data-testid="detector-parametros-padrao" className="analise-botao-secundario" onClick={voltarAoPadrao}>
          <RotateCcw size={14} aria-hidden="true"/>Voltar ao padrão</button>
      </div>
    </form>}

    {erro && <p data-testid="detector-erro" role="alert" className="analise-motivo">{erro}{" "}
      <button type="button" className="analise-link" onClick={() => setTentativa(valor => valor + 1)}>Tentar de novo</button></p>}
    {carregando && !resposta && <p role="status" className="analise-vazio"><LoaderCircle size={18} className="animate-spin" aria-hidden="true"/>Calculando os sinais…</p>}

    {resposta && r && <div data-testid="detector-resumo" data-territorios={resposta.resumo.territorios} className="ferramenta-resumo-niveis" role="group"
      aria-label="Resumo dos níveis: toque num deles para filtrar a lista">
      {ESTADOS_DO_ALERTA.filter(estado => estado !== "sem_nivel" || (resposta.resumo.niveis.sem_nivel ?? 0) > 0).map(estado => {
        const n = resposta.resumo.niveis[estado] ?? 0;
        return <button key={estado} type="button" data-testid={"detector-resumo-" + estado} data-quantos={n} aria-pressed={filtros.nivel === estado}
          className={"ferramenta-resumo-nivel ferramenta-resumo-nivel-" + estado}
          onClick={() => mudarFiltros({ nivel: filtros.nivel === estado ? "todos" : estado })}>{textoDaContagem(estado as EstadoDoAlerta, n)}</button>;
      })}
      <span className="ferramenta-apoio">de {formatarInteiro(resposta.resumo.territorios)} {resposta.resumo.territorios === 1 ? "território" : "territórios"} ·
        um nível por território: o maior entre os seus sinais</span>
    </div>}

    {resposta && <div className="ferramenta-acoes analise-nao-imprimir">
      <div role="group" aria-label="Lista, mapa ou gráfico" className="ferramenta-modos">
        <button type="button" data-testid="detector-vista-lista" className="analise-botao-secundario" aria-pressed={vista === "lista"}
          onClick={() => setVista("lista")}><List size={14} aria-hidden="true"/>Lista</button>
        <button type="button" data-testid="detector-vista-mapa" className="analise-botao-secundario" aria-pressed={vista === "mapa"}
          onClick={() => setVista("mapa")}><IconeDoMapa size={14} aria-hidden="true"/>Mapa</button>
        <button type="button" data-testid="detector-vista-grafico" className="analise-botao-secundario" aria-pressed={vista === "grafico"}
          onClick={() => setVista("grafico")}><ChartScatter size={14} aria-hidden="true"/>Gráfico</button>
      </div>
      <button type="button" data-testid="detector-exportar-csv" className="analise-botao-secundario" disabled={!filtradas.length}
        onClick={() => baixar("detector_de_sinais_" + resposta.janela.fim + ".csv", csvDoDetector(resposta, filtradas), "text/csv;charset=utf-8")}>
        <Download size={14} aria-hidden="true"/>Exportar a lista (CSV)</button>
      <button type="button" data-testid="detector-exportar-metodo" className="analise-botao-secundario"
        onClick={() => baixar("detector_de_sinais_metodo_" + resposta.janela.fim + ".json", metodoDoDetector(resposta), "application/json")}>
        <Download size={14} aria-hidden="true"/>Exportar o método (JSON)</button>
      <span className="ferramenta-apoio">Territórios: {p.resumoDaSelecao}{" "}
        <button type="button" data-testid="detector-alterar-selecao" className="analise-link" onClick={p.onAlterarSelecao}>Alterar a seleção</button></span>
    </div>}

    {resposta && vista !== "lista" && <div data-testid="detector-visual" data-vista={vista} className="ferramenta-visual">
      {vista === "mapa" && <MapaDosNiveis resposta={resposta} linhas={filtradas} sinal={filtros.sinal} onAbrir={abrirDoDesenho}/>}
      {vista === "grafico" && <BolhasDoContexto resposta={resposta} linhas={filtradas} sinal={filtros.sinal} onAbrir={abrirDoDesenho}/>}
    </div>}

    {resposta && r && <div className="ferramenta-rolagem">
      <table data-testid="detector-tabela" data-linhas={filtradas.length} data-ordem={ordem} className="analise-tabela ferramenta-tabela ferramenta-lista">
        <caption className="ferramenta-apoio">Situação em {competenciaCurta(resposta.janela.fim)}, com os registros desde{" "}
          {competenciaCurta(resposta.janela.inicio)}. Toque no território para ver a série e os 12 sinais.
          {resposta.comparacao.estado === "comparacao_nao_habilitada" && <span data-testid="detector-comparacao" data-estado={resposta.comparacao.estado}>
            {" "}Os sinais comparados em 2 anos (8 a 10) não são avaliados de {competenciaCurta(resposta.comparacao.de)} a{" "}
            {competenciaCurta(resposta.comparacao.ate)}: {resposta.comparacao.motivo ?? "a população da base não é comparável de um ano para o outro nesta janela"}.
            A variação é calculada {textoDosTrechos(resposta.comparacao.trechos)}.</span>}
          {resposta.comparacao.estado === "comparavel" && <span data-testid="detector-comparacao" data-estado="comparavel">
            {" "}Os sinais comparados em 2 anos (8 a 10) usam a variação de {competenciaCurta(resposta.comparacao.de)} a{" "}
            {competenciaCurta(resposta.comparacao.ate)}.</span>}
          {resposta.comparacao.estado !== "comparavel" && resposta.comparacao.estado !== "comparacao_nao_habilitada" &&
            <span data-testid="detector-comparacao" data-estado={resposta.comparacao.estado}>{" "}Os sinais comparados em 2 anos (8 a 10) não são avaliados
              nesta data: falta o registro de dois anos antes.</span>}
        </caption>
        <thead><tr>
          <th scope="col" aria-sort={ordem === "nome" ? "ascending" : undefined}>{cabecaDeOrdem("Território", "nome", "detector-ordem-nome")}</th>
          <th scope="col" aria-sort={ordem === "nivel" ? "descending" : undefined}><span className="ferramenta-th-com-entenda">
            {cabecaDeOrdem("Alerta", "nivel", "detector-ordem-nivel")}
            {resposta.entenda.alerta && <Entenda sobre="Alerta" texto={resposta.entenda.alerta.texto} exemplo={resposta.entenda.alerta.exemplo}
              testid="detector-entenda-alerta" onCompleta={abrirOMetodo}/>}</span></th>
          <th scope="col"><span className="ferramenta-th-com-entenda">Por quê
            {resposta.entenda.termos && <Entenda sobre="Termos da lista" texto={resposta.entenda.termos.texto} exemplo={resposta.entenda.termos.exemplo}
              testid="detector-entenda-termos" onCompleta={abrirOMetodo}/>}</span></th>
          <th scope="col" aria-sort={ordem === "numero" ? "ascending" : undefined}>{cabecaDeOrdem("Último registro", "numero", "detector-ordem-numero")}</th>
        </tr></thead>
        <tbody>
          {naPagina.map(linha => {
            const registro = textoDoRegistro(linha), tipo = tipoDoTerritorio(linha, r), alerta = textoDoAlerta(linha);
            const detalhe = detalhes[linha.id], expandida = aberto === linha.id;
            return <Fragment key={linha.id}>
              <tr data-testid="detector-linha" data-id={linha.id} data-tipo={linha.tipo} data-alerta={estadoDoAlerta(linha)}
                data-sinais={linha.alerta.sinais.map(item => item.sinal).join(" ")} data-registro={registro.marca}>
                <th scope="row" data-rotulo="Território" className="ferramenta-territorio">
                  <button type="button" data-testid="detector-abrir" className="ferramenta-abrir" aria-expanded={expandida}
                    aria-label={(expandida ? "Fechar os detalhes de " : "Ver os detalhes de ") + linha.rotulo}
                    onClick={() => setAberto(atual => atual === linha.id ? null : linha.id)}>
                    {expandida ? <ChevronDown size={15} aria-hidden="true"/> : <ChevronRight size={15} aria-hidden="true"/>}
                    <span>{linha.rotulo}</span></button>
                  {tipo && <span className="ferramenta-apoio">{tipo}</span>}
                </th>
                <td data-rotulo="Alerta" data-testid="detector-alerta" data-estado={alerta.estado}>
                  {alerta.nivel ? <><Nivel nivel={alerta.nivel}/><span data-testid="detector-criterio" className="ferramenta-apoio ferramenta-criterio-tipo">
                    {alerta.criterio}</span></> : <span className="ferramenta-sem-nivel">{alerta.texto}</span>}
                </td>
                <td data-rotulo="Por quê" data-testid="detector-por-que" className="ferramenta-coluna-larga">{textoDoPorQue(linha, r)}</td>
                <td data-rotulo="Último registro" data-testid="detector-ultimo">{textoDaUltima(linha, resposta.janela.fim, r)}
                  {registro.marca !== "normal" && <span data-testid="detector-registro" data-marca={registro.marca}
                    className={"ferramenta-registro ferramenta-registro-" + registro.marca}>{registro.texto}</span>}</td>
              </tr>
              {expandida && <tr className="ferramenta-linha-detalhe"><td colSpan={4}>
                {!detalhe ? <p role="status" className="ferramenta-apoio"><LoaderCircle size={14} className="animate-spin inline" aria-hidden="true"/> Abrindo os detalhes…</p>
                  : "erro" in detalhe ? <p role="alert" className="analise-motivo">{detalhe.erro}</p>
                    : <DetalheDoTerritorio detalhe={detalhe} linha={linha} resposta={resposta} patamar={patamarARecuperar(linha)}
                      onAbrirNoSimulador={p.onAbrirNoSimulador ? () => p.onAbrirNoSimulador!(alvoDoSimulador(linha, resposta)) : undefined}
                      onSimularRecuperacao={p.onSimularRecuperacao && patamarARecuperar(linha) !== null
                        ? () => p.onSimularRecuperacao!(alvoDoSimulador(linha, resposta), patamarARecuperar(linha)!) : undefined}/>}
              </td></tr>}
            </Fragment>;
          })}
          {!filtradas.length && <tr><td colSpan={4} data-testid="detector-sem-linhas" className="ferramenta-apoio">Nenhum território da seleção passa nos filtros.</td></tr>}
        </tbody>
      </table>
    </div>}
    {resposta && paginas > 1 && <nav data-testid="detector-paginas" className="ferramenta-paginas analise-nao-imprimir" aria-label="Páginas da lista">
      <button type="button" className="analise-botao-secundario" disabled={paginaAtual === 0} onClick={() => setPagina(paginaAtual - 1)}>Anterior</button>
      <span className="ferramenta-apoio">Página {paginaAtual + 1} de {paginas} · {formatarInteiro(filtradas.length)} territórios</span>
      <button type="button" className="analise-botao-secundario" disabled={paginaAtual >= paginas - 1} onClick={() => setPagina(paginaAtual + 1)}>Próxima</button>
    </nav>}

    {resposta && r && <div ref={metodo} className="ferramenta-metodo">
      <button type="button" data-testid="detector-metodo-botao" className="analise-link" aria-expanded={verMetodo}
        onClick={() => setVerMetodo(valor => !valor)}>{verMetodo ? "Fechar “Como foi calculado”" : "Como foi calculado"}</button>
      {verMetodo && <div data-testid="detector-metodo" className="ferramenta-metodo-corpo">
        <ul className="ferramenta-notas">{resposta.notas.map(nota => <li key={nota}>{nota}</li>)}</ul>
        <table data-testid="detector-niveis" className="analise-tabela ferramenta-tabela">
          <caption className="ferramenta-apoio">Os três níveis: raridade = (mudanças anteriores iguais ou piores + 1) ÷ (total de mudanças anteriores + 1).</caption>
          <thead><tr><th scope="col">Nível</th><th scope="col">Raridade padrão</th><th scope="col">Comparações anteriores necessárias</th></tr></thead>
          <tbody>{resposta.niveis.map(item => <tr key={item.chave}><th scope="row"><Nivel nivel={item.chave}/></th>
            <td>1 em cada {formatarInteiro(item.umEm)}</td><td>pelo menos {formatarInteiro(item.pede)}</td></tr>)}</tbody>
        </table>
        <TabelaDaRegua regua={resposta.calibracao} faixas={resposta.calibracao.perda} o_que="queda" testid="detector-calibracao" r={r}
          titulo={"Queda recente (sinal 6), " + r.unidades + ": a partir de que queda ela é rara, por porte (o número de " + r.profissionais + " antes)."}/>
        <TabelaDaRegua regua={resposta.calibracao} faixas={resposta.calibracao.patamar} o_que="afastamento" testid="detector-calibracao-patamar" r={r}
          titulo={"Abaixo do que já teve (sinal 7), " + r.unidades + ": a partir de que afastamento do patamar ele é raro, por porte do patamar."}/>
        {resposta.calibracaoDosEstados && <TabelaDaRegua regua={resposta.calibracaoDosEstados} faixas={resposta.calibracaoDosEstados.perda.filter(faixa => faixa.comparacoes > 0)}
          o_que="queda" testid="detector-calibracao-estados" r={r}
          titulo={"Queda recente (sinal 6), " + r.grupos + " como unidade: a régua própria, com a base dos " + r.grupos + "."}/>}
        <p className="ferramenta-apoio">Método {resposta.versao} · base {resposta.fonte.base} ({resposta.fonte.categoria.toLowerCase()}), versão{" "}
          {resposta.fonte.versao.slice(0, 12)} · nesta data, {formatarInteiro(resposta.calibracao.monitoramento.raras)} de{" "}
          {formatarInteiro(resposta.calibracao.monitoramento.avaliadas)} {r.unidades} tiveram uma mudança rara (1 em cada 20) no último registro
          {resposta.calibracao.monitoramento.taxaPct !== null ? ": " + formatarPct(resposta.calibracao.monitoramento.taxaPct) + ", para um esperado de cerca de " +
            formatarPct(resposta.calibracao.monitoramento.esperadoPct ?? 5).replace(",0%", "%") : ""}.</p>
      </div>}
    </div>}
  </section>;
}
