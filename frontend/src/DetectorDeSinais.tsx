import { Fragment, useEffect, useMemo, useRef, useState, type RefObject } from "react";
import { ArrowDownUp, ChartScatter, ChevronDown, ChevronRight, Download, FileText, List, LoaderCircle, Map as IconeDoMapa, RotateCcw, SlidersHorizontal } from "lucide-react";
import { BolhasDoContexto, MapaDosNiveis, SerieDaTaxa } from "./DetectorGraficos";
import Entenda from "./Entenda";
import { SECOES_DAS_FICHAS, linkDaFicha } from "./fichas";
import { tamanhoDoGrafico, useLargura } from "./PainelChart";
import { ErroDoMotor, pedirAoMotor, type FonteDoMotor, type RotulosTerritoriais } from "./painelApi";
import {
  ESTADOS_DO_ALERTA, SEM_FILTROS, alvoDoSimulador, rotuloDoCriterio, artigoDaUnidade, competenciaCurta, criteriosEmFrases, csvDoDetector, estadoDoAlerta,
  entendaDaLista, filtrarLinhas, filtrosDeSinal, formatarInteiro, formatarPct, formatarTaxa, linhasDoTerritorio, metodoDoDetector, nomeDoEstado, nomeDoSinal,
  normalizarDetalhe, metaDaRecuperacao, normalizarDetector, comODetalhe, MemoriaDoDetector, ordenarLinhas, parametrosPersonalizados, patamarARecuperar, precisaDoDetalhe, profissionais,
  ressalvasDaLista, rotuloDoCampo, sinalDoAlertaNoHistorico, textoDaContagem, textoDaMesmaQueda, textoDaUltima, textoDoAlerta, textoDoPorQue, textoDoRegistro,
  textoDosTrechos, tipoDoTerritorio, NOMES_DOS_NIVEIS,
  type AlvoDoSimulador, type DetalheDoDetector, type DetalheQueChegou, type DetalhesDoPedido, type EstadoDoAlerta, type FenomenoDoDetalhe, type FiltrosDoDetector,
  type LinhaDoDetector, type NivelDoAlerta, type OpcoesDaBase, type OpcoesDoDetector, type OrdemDoDetector, type ParametrosDoDetector,
  type RespostaDoDetector, type SelecaoDasFerramentas,
} from "./detectorModel";

// Detector de Sinais Territoriais (comando V23, Proposta V3, Parte B; Docs/DETECTOR_DE_SINAIS.md). A primeira tela é uma lista de
// cinco colunas (Território · Sinal · Alerta · Por quê · Último registro; desde o AJ-04, de 18/11/2026, cada sinal com nível numa
// linha, com o nome do sinal em coluna própria, e o território e o último registro uma vez para o conjunto das linhas; antes, quatro
// colunas, com o sinal principal e "(+N sinais)"), com o resumo dos níveis no alto, clicável como filtro, os
// filtros numa linha (Até, Nível, Sinal e Buscar) e as visões Lista, Mapa e Gráfico. Cada território tem um nível só — moderado,
// elevado ou crítico, o maior entre os seus sinais, sem soma nem índice —, sempre escrito e com o tipo de critério ("comparado
// com a base" ou "limite fixo"); quando a base não tem comparações bastantes, a tela diz "sem comparações suficientes", com
// os números. "Ajustar critérios" mostra os limites em frases, com os campos dentro delas: trocar um valor torna a configuração
// exploratória, com aviso no alto, e "Voltar ao padrão" fica sempre à vista. O detalhe de um território traz a série e os 12
// sinais em quatro grupos (Quantos há, Como mudou, Comparado com outros, Onde fica), mais Juntos; em cada sinal, o nível, uma
// frase e o "Entenda" (Entenda.tsx), com a explicação inteira em "Ver explicação completa". Todo número e todo texto de resultado
// vêm do motor (POST /api/detector), que calcula sem o provedor de IA. A tela só filtra, ordena e desenha. Desde o AJ-03 (18/11/2026),
// a informação de método e técnica ("Como foi calculado": as notas, os níveis, a régua da data e a linha de versões) saiu da tela e
// está na ficha metodológica em PDF (o link "Ficha metodológica (PDF)" e o "Ver explicação completa" dos "Entenda" da lista); os
// números da régua e do monitoramento da data continuam em "Exportar o método (JSON)". Junto da lista, ficam as ressalvas de leitura.
// Vale para qualquer base (seção A.3): com uma planilha enviada, o pedido leva o que descreve a planilha (os nomes, as premissas e
// a categoria, como no painel); o que a base não sustenta aparece como "Indisponível nesta base", com o motivo, e o mapa e o
// gráfico ficam desligados, também com o motivo, quando faltam as coordenadas ou a população.

const POR_PAGINA = 50;
const SEM_DETALHES: DetalhesDoPedido["itens"] = {};
/** A base da página (ADT_BASE_DA_PAGINA), para o link da ficha metodológica em PDF. */
const BASE = import.meta.env.BASE_URL || "/";
type Props = {
  fonte: FonteDoMotor;
  /** A seleção em uso (a da Seleção de Territórios); null sem territórios. */
  selecao: SelecaoDasFerramentas | null;
  /** Numa planilha enviada, o que o pedido diz dela (os nomes, as premissas e a categoria), como no pedido do painel. */
  daBase?: OpcoesDaBase;
  /** Numa planilha enviada, os nomes do painel "Colunas", para o gráfico e a série da taxa (na base do Brasil, os do Brasil). */
  rotulosDoPainel?: RotulosTerritoriais;
  /** O que da seleção ficou fora da ferramenta, e por quê (numa planilha, o grupo de cima como unidade não tem contagem própria). */
  avisoDaSelecao?: string | null;
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
  // O desenho é feito na largura que o gráfico tem na tela (e não encolhido de 640 px): o texto dos eixos mantém 12 px também no
  // celular, onde o gráfico fica mais alto e mostra menos datas no eixo (revisão das capturas de 15/11/2026).
  const [refDoGrafico, medida] = useLargura(640, !valores.length);
  if (!valores.length) return <p className="ferramenta-apoio">Sem registros na série.</p>;
  const { largura, altura, estreito } = tamanhoDoGrafico(medida, 720, 170, 220);
  const esquerda = 44, direita = 34, topo = 12, base = 34;
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
  const deQuantosAnos = estreito ? 4 : 2;
  return <figure ref={refDoGrafico as RefObject<HTMLElement>} data-testid="detector-serie" data-largura={largura} className="ferramenta-serie">
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
      {pontos.map((ponto, indice) => ponto.competencia.endsWith(mes) && (indice === pontos.length - 1 ||
        (Number(ponto.competencia.slice(0, 4)) % deQuantosAnos === 0 && pontos.length - 1 - indice >= deQuantosAnos))
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
  sem_dado: "Sem dado para avaliar", nao_avaliado: "Não avaliado", contexto: "Só contexto", juntos: "", indisponivel: "Indisponível nesta base" };

/** Um sinal no detalhe: o nível (com o tipo de critério), uma frase, o "Entenda" e, quando pedida, a explicação completa. */
function SinalDoTerritorio({ sinal, aberto, onAlternar }: { sinal: FenomenoDoDetalhe; aberto: boolean; onAlternar: (abrir?: boolean) => void }) {
  const estado = sinal.nivel ? null : ESTADOS_DO_NIVEL[sinal.estadoDoNivel] ?? "Sem alerta";
  return <li data-testid="detector-fenomeno" data-chave={sinal.chave} data-nivel={sinal.nivel ?? ""} data-estado={sinal.estadoDoNivel}
    className="ferramenta-fenomeno">
    <div className="ferramenta-sinal">
      <span className="ferramenta-sinal-nome"><span className="ferramenta-apoio">Sinal {sinal.numero}</span>{sinal.nome}</span>
      <span data-testid="detector-fenomeno-nivel" className="ferramenta-sinal-nivel">
        {sinal.nivel ? <><Nivel nivel={sinal.nivel}/><span data-testid="detector-fenomeno-criterio" className="ferramenta-apoio">
          {rotuloDoCriterio(sinal.criterioDoNivel)}{sinal.exploratorio ? " · exploratório" : ""}</span></>
          : estado ? <span className="ferramenta-sem-nivel">{estado}</span> : null}
      </span>
      {/* O sinal que a base não sustenta (sem população, coordenadas, grupo de cima ou série anual): a frase é o motivo. */}
      <span data-testid="detector-fenomeno-situacao" className="ferramenta-sinal-frase">{sinal.estadoDoNivel === "indisponivel" ? sinal.observado : sinal.situacao}
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

function DetalheDoTerritorio({ detalhe, linha, resposta, patamar, rotulosDoPainel, onAbrirNoSimulador, onSimularRecuperacao }: { detalhe: DetalheDoDetector;
  linha: LinhaDoDetector; resposta: RespostaDoDetector; rotulosDoPainel?: RotulosTerritoriais;
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
      {alerta.nivel ? <><span data-testid="detector-detalhe-sinal">{nomeDoSinal(linha.alerta.sinal ?? "", r)}</span><Nivel nivel={alerta.nivel}/>
        <span className="ferramenta-apoio">{alerta.criterio}</span></> : <span className="ferramenta-sem-nivel">{alerta.texto}</span>}
      <span>{textoDoPorQue(linha, r)}</span>
      {mesmaQueda && <span data-testid="detector-mesma-queda" className="ferramenta-apoio">{mesmaQueda}</span>}
    </p>
    <p className="ferramenta-apoio">Contagem: {detalhe.unidade}.{detalhe.membros.length > 0 && " Componentes: " + detalhe.membros.join(", ") + "."}
      {detalhe.depoisDaQuebra && " Os indicadores deste território começam em " + competenciaCurta(detalhe.inicioDoTerritorio) + ", depois da quebra de fonte."}</p>
    <SerieObservada detalhe={detalhe}/>
    <SerieDaTaxa detalhe={detalhe} profissionais={r.profissionais} rotulosDoPainel={rotulosDoPainel} feminino={artigoDaUnidade(r) === "a"}/>
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
        title={"Abre o Simulador com a meta hipotética de voltar ao patamar: " + profissionais(metaDaRecuperacao(patamar), r) +
          "; a meta pode ser trocada"} onClick={onSimularRecuperacao}>Simular recuperação</button>}
    </div>
    {/* A meta é um número inteiro: o patamar (uma média, que pode ter decimal) arredondado para cima; a frase diz de onde ela vem. */}
    {onSimularRecuperacao && patamar !== null && <p data-testid="detector-recuperacao-apoio" data-meta={metaDaRecuperacao(patamar)} className="ferramenta-apoio">
      “Simular recuperação” abre o Simulador de Cenários com uma meta hipotética: voltar ao patamar, {profissionais(metaDaRecuperacao(patamar), r)}{" "}
      ({metaDaRecuperacao(patamar) - patamar > 1e-9 ? "o patamar é de " + formatarTaxa(patamar).replace(/0$/, "") + ", a" : "a"} maior média de dois anos seguidos
      antes dos registros mais recentes{metaDaRecuperacao(patamar) - patamar > 1e-9 ? ", arredondado para cima" : ""}). A meta é uma hipótese que você pode trocar; o
      resultado é um cenário, não uma previsão.</p>}
    {verHistorico && <div className="ferramenta-rolagem"><table data-testid="detector-historico" className="analise-tabela ferramenta-tabela">
      <caption className="ferramenta-apoio">Histórico de sinais na janela (sinais 1 a 7): cada data avaliada só com o que era conhecido nela.</caption>
      <thead><tr><th scope="col">Registro</th><th scope="col">Número</th><th scope="col">Alerta</th><th scope="col">{nomeDoSinal("estrutural", r)}</th>
        <th scope="col">Queda desde o registro anterior</th><th scope="col">Ante o patamar</th><th scope="col">Série anual</th></tr></thead>
      <tbody>{detalhe.historico.map(passo => <tr key={passo.competencia} data-competencia={passo.competencia} data-alerta={passo.alerta ?? ""}>
        <th scope="row">{competenciaCurta(passo.competencia)}</th>
        <td>{passo.valor === null ? "sem registro" : formatarInteiro(passo.valor)}</td>
        <td data-testid="detector-historico-alerta">{passo.alerta ? <><Nivel nivel={passo.alerta}/><span className="ferramenta-apoio block">
          {sinalDoAlertaNoHistorico(passo, r)}</span></> : "—"}</td>
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
  // Os detalhes do pedido à vista, com a chave dele (AJ-08): a resposta atrasada de outro pedido não entra.
  const [detalhesDoPedido, setDetalhesDoPedido] = useState<DetalhesDoPedido>({ chave: "", itens: {} });
  const [verCriterios, setVerCriterios] = useState(false);
  const [rascunho, setRascunho] = useState<Record<string, Record<string, string>>>({});
  const [vista, setVista] = useState<Vista>("lista");
  // A memória da tela (AJ-08): as listas e, com cada uma, os detalhes que chegaram certos, por pedido (os últimos seis).
  const memoria = useRef(new MemoriaDoDetector());
  // AJ-04: os detalhes que a lista pede para ter a frase de cada sinal (os em curso e o controle do pedido em uso).
  const emCurso = useRef(new Set<string>());
  const doPedido = useRef<AbortController | null>(null);
  const [fila, setFila] = useState(0);
  // O pedido a que a lista na tela responde: enquanto a lista de um pedido novo não chega, a de antes continua à vista, e a página não
  // pede detalhes para ela com o pedido novo.
  const [chaveDaResposta, setChaveDaResposta] = useState("");

  const pedido: OpcoesDoDetector | null = useMemo(() => p.selecao ? { ...p.selecao, ...(p.daBase ?? {}), ...(janela.inicio || janela.fim ? { janela } : {}),
    ...(parametros ? { parametros } : {}) } : null, [p.selecao, p.daBase, janela, parametros]);
  // A planilha enviada é identificada pelo arquivo, pela aba e pelo mapeamento: trocar qualquer um deles é outra base.
  const daPlanilha = p.fonte.tipo === "arquivo" ? JSON.stringify([p.fonte.arquivo ? [p.fonte.arquivo.name, p.fonte.arquivo.size, p.fonte.arquivo.lastModified] : null,
    p.fonte.sheet, p.fonte.mapping]) + "::" : "";
  const chave = pedido ? p.fonte.datasetVersion + "::" + daPlanilha + JSON.stringify(pedido) : "";
  const detalhes = detalhesDoPedido.chave === chave ? detalhesDoPedido.itens : SEM_DETALHES;
  /** Um detalhe que chegou do motor (AJ-08): o que chegou certo fica na memória do pedido dele; na tela, só entra se o pedido à vista
   * ainda é o mesmo. */
  const chegou = (chaveDoPedido: string, id: string, detalhe: DetalheQueChegou) => {
    memoria.current.guardarDetalhe(chaveDoPedido, id, detalhe);
    setDetalhesDoPedido(atual => comODetalhe(atual, chaveDoPedido, id, detalhe));
  };

  // A lista: pedida ao motor a cada mudança da seleção, da janela ou dos critérios; a resposta de um pedido igual vem da memória,
  // com os detalhes que já tinham chegado certos para ele (AJ-08): as frases já buscadas não são pedidas de novo.
  useEffect(() => {
    setAberto(null); setDetalhesDoPedido({ chave, itens: memoria.current.detalhesDe(chave) }); setPagina(0);
    if (!pedido) { setResposta(null); setChaveDaResposta(""); setErro(null); setCarregando(false); return; }
    const guardada = memoria.current.lista(chave);
    if (guardada) { setResposta(guardada); setChaveDaResposta(chave); setErro(null); setCarregando(false); return; }
    const controle = new AbortController();
    setCarregando(true); setErro(null);
    pedirAoMotor(p.fonte, "/api/detector", pedido, controle.signal)
      .then(bruto => {
        if (controle.signal.aborted) return;
        const lida = normalizarDetector(bruto);
        memoria.current.guardarLista(chave, lida);
        setResposta(lida); setChaveDaResposta(chave);
      })
      .catch((exc: unknown) => {
        if (controle.signal.aborted) return;
        setErro(exc instanceof ErroDoMotor || exc instanceof Error ? exc.message : "Não foi possível calcular os sinais.");
      })
      .finally(() => { if (!controle.signal.aborted) setCarregando(false); });
    return () => controle.abort();
  }, [chave, tentativa]);

  // Os detalhes de um território, pedidos ao abrir a linha (a não ser que a lista já os tenha pedido).
  useEffect(() => {
    if (!aberto || !pedido || detalhes[aberto] || emCurso.current.has(aberto)) return;
    const controle = new AbortController(), id = aberto, chaveDoPedido = chave;
    pedirAoMotor(p.fonte, "/api/detector", { ...pedido, detalhe: id }, controle.signal)
      .then(bruto => { if (!controle.signal.aborted) chegou(chaveDoPedido, id, normalizarDetalhe(bruto)); })
      .catch((exc: unknown) => { if (!controle.signal.aborted) chegou(chaveDoPedido, id,
        { erro: exc instanceof Error ? exc.message : "Não foi possível abrir os detalhes." }); });
    return () => controle.abort();
  }, [aberto, chave]);

  const filtradas = useMemo(() => resposta ? ordenarLinhas(filtrarLinhas(resposta.linhas, filtros), ordem) : [], [resposta, filtros, ordem]);
  const paginas = Math.max(1, Math.ceil(filtradas.length / POR_PAGINA));
  const paginaAtual = Math.min(pagina, paginas - 1);
  const naPagina = useMemo(() => filtradas.slice(paginaAtual * POR_PAGINA, (paginaAtual + 1) * POR_PAGINA), [filtradas, paginaAtual]);

  // AJ-04: a frase de cada sinal com nível vem do detalhe do território (`fenomenos[].situacao`). A lista pede o detalhe só dos
  // territórios à vista com mais de um sinal com nível, dois de cada vez, e só depois que a lista do pedido em uso chegou; a resposta
  // fica com os detalhes que a pessoa abre. Na troca do pedido (a seleção, a janela ou os critérios), os pedidos de antes param; o
  // que já tinha chegado certo fica na memória do pedido dele, e voltar a ele não pede de novo (AJ-08).
  useEffect(() => {
    doPedido.current?.abort();
    doPedido.current = new AbortController();
    emCurso.current.clear();
    return () => doPedido.current?.abort();
  }, [chave]);
  useEffect(() => {
    const controle = doPedido.current;
    if (!pedido || !resposta || chaveDaResposta !== chave || !controle) return;
    for (const linha of naPagina) {
      if (emCurso.current.size >= 2) break;
      if (!precisaDoDetalhe(linha) || detalhes[linha.id] || emCurso.current.has(linha.id)) continue;
      const id = linha.id, chaveDoPedido = chave;
      emCurso.current.add(id);
      pedirAoMotor(p.fonte, "/api/detector", { ...pedido, detalhe: id }, controle.signal)
        .then(bruto => { if (!controle.signal.aborted) chegou(chaveDoPedido, id, normalizarDetalhe(bruto)); })
        .catch((exc: unknown) => { if (!controle.signal.aborted) chegou(chaveDoPedido, id,
          { erro: exc instanceof Error ? exc.message : "Não foi possível abrir os detalhes." }); })
        .finally(() => { emCurso.current.delete(id); if (!controle.signal.aborted) setFila(valor => valor + 1); });
    }
  }, [naPagina, detalhes, resposta, chaveDaResposta, fila]);
  const competencias = resposta?.competencias ?? [];
  const inicioEmUso = janela.inicio ?? resposta?.janela.inicio ?? "", fimEmUso = janela.fim ?? resposta?.janela.fim ?? "";
  const r = resposta?.fonte.rotulos;
  const daLista = entendaDaLista(r ?? { profissional: "", profissionais: "", unidade: "", unidades: "", grupo: "", grupos: "", todo: "" },
    naPagina.find(linha => linha.ultima) ?? null, resposta?.janela.fim ?? "");
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
        exemplo={resposta.entenda.ferramenta.exemplo} testid="detector-entenda-ferramenta"
        completaHref={linkDaFicha(BASE, "detector", SECOES_DAS_FICHAS.detector.ferramenta)}/>}
    </div>
    <p className="analise-subtitulo">Compara cada território com o que é comum na própria base. Descreve os registros; não diz se o atendimento é
      suficiente nem onde prover.</p>
  </header>;

  if (!p.selecao) return <section data-testid="detector" data-estado="sem-selecao" aria-labelledby="detector-titulo" className="ferramenta">
    {cabecalho}
    <p data-testid="detector-sem-selecao" role="status" className="analise-motivo">Nenhum território selecionado.{" "}
      <button type="button" className="analise-link" onClick={p.onAlterarSelecao}>Selecionar os territórios</button></p>
  </section>;

  // O que a base não sustenta (sinal → motivo): os critérios e o filtro "Sinal" ficam só com os sinais que existem nela; o mapa
  // pede coordenadas, e o gráfico, a distância (população e coordenadas).
  const indisponiveis = resposta?.indisponiveis ?? {};
  const criterios = r ? criteriosEmFrases(r).filter(criterio => !indisponiveis[criterio.sinal]) : [];
  const semMapa = resposta && !resposta.fonte.tem.coordenadas ? "A base não tem coordenadas com o referencial informado: não há pontos para o mapa." : null;
  const semGrafico = resposta ? indisponiveis.contexto ?? null : null;
  const vistaEmUso: Vista = (vista === "mapa" && semMapa) || (vista === "grafico" && semGrafico) ? "lista" : vista;
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
    {p.avisoDaSelecao && <p data-testid="detector-aviso-da-selecao" role="note" className="ferramenta-aviso">{p.avisoDaSelecao}</p>}
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
          {filtrosDeSinal(r).filter(item => !indisponiveis[item.chave]).map(item => <option key={item.chave} value={item.chave}>{item.rotulo}</option>)}
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
      {Object.keys(indisponiveis).length > 0 && r && <p data-testid="detector-criterios-indisponiveis" className="ferramenta-apoio">Sem critérios a ajustar
        nesta base: {Object.keys(indisponiveis).map(sinal => nomeDoSinal(sinal, r).toLowerCase()).join(", ")}. O motivo de cada um está no detalhe do
        território e no perfil da base.</p>}
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
        <button type="button" data-testid="detector-vista-lista" className="analise-botao-secundario" aria-pressed={vistaEmUso === "lista"}
          onClick={() => setVista("lista")}><List size={14} aria-hidden="true"/>Lista</button>
        <button type="button" data-testid="detector-vista-mapa" className="analise-botao-secundario" aria-pressed={vistaEmUso === "mapa"}
          disabled={!!semMapa} title={semMapa ?? undefined} onClick={() => setVista("mapa")}><IconeDoMapa size={14} aria-hidden="true"/>Mapa</button>
        <button type="button" data-testid="detector-vista-grafico" className="analise-botao-secundario" aria-pressed={vistaEmUso === "grafico"}
          disabled={!!semGrafico} title={semGrafico ?? undefined} onClick={() => setVista("grafico")}><ChartScatter size={14} aria-hidden="true"/>Gráfico</button>
      </div>
      <button type="button" data-testid="detector-exportar-csv" className="analise-botao-secundario" disabled={!filtradas.length}
        onClick={() => baixar("detector_de_sinais_" + resposta.janela.fim + ".csv", csvDoDetector(resposta, filtradas), "text/csv;charset=utf-8")}>
        <Download size={14} aria-hidden="true"/>Exportar a lista (CSV)</button>
      <button type="button" data-testid="detector-exportar-metodo" className="analise-botao-secundario"
        onClick={() => baixar("detector_de_sinais_metodo_" + resposta.janela.fim + ".json", metodoDoDetector(resposta), "application/json")}>
        <Download size={14} aria-hidden="true"/>Exportar o método (JSON)</button>
      <a data-testid="detector-ficha" className="analise-botao-secundario" href={linkDaFicha(BASE, "detector")} target="_blank" rel="noopener">
        <FileText size={14} aria-hidden="true"/>Ficha metodológica (PDF)<span className="sr-only"> (abre numa nova aba)</span></a>
      <span className="ferramenta-apoio">Territórios: {p.resumoDaSelecao}{" "}
        <button type="button" data-testid="detector-alterar-selecao" className="analise-link" onClick={p.onAlterarSelecao}>Alterar a seleção</button></span>
    </div>}

    {resposta && (semMapa || semGrafico) && <p data-testid="detector-vistas-motivo" className="ferramenta-apoio analise-nao-imprimir">
      {[semMapa ? "Mapa indisponível: " + semMapa : "", semGrafico ? "Gráfico indisponível: " + semGrafico : ""].filter(Boolean).join(" ")}</p>}
    {resposta && vistaEmUso !== "lista" && <div data-testid="detector-visual" data-vista={vistaEmUso} className="ferramenta-visual">
      {vistaEmUso === "mapa" && <MapaDosNiveis resposta={resposta} linhas={filtradas} sinal={filtros.sinal} onAbrir={abrirDoDesenho}/>}
      {vistaEmUso === "grafico" && <BolhasDoContexto resposta={resposta} linhas={filtradas} sinal={filtros.sinal} onAbrir={abrirDoDesenho}
        rotulosDoPainel={p.rotulosDoPainel}/>}
    </div>}

    {resposta && r && <div className="ferramenta-rolagem detector-rolagem">
      <table data-testid="detector-tabela" data-linhas={filtradas.length} data-ordem={ordem} className="analise-tabela ferramenta-tabela ferramenta-lista">
        <caption className="ferramenta-apoio">Situação em {competenciaCurta(resposta.janela.fim)}, com os registros desde{" "}
          {competenciaCurta(resposta.janela.inicio)}. Cada sinal com nível tem uma linha; toque no território para ver a série e os 12 sinais.
          {resposta.comparacao.estado === "comparacao_nao_habilitada" && <span data-testid="detector-comparacao" data-estado={resposta.comparacao.estado}>
            {" "}Os sinais comparados em 2 anos (8 a 10) não são avaliados de {competenciaCurta(resposta.comparacao.de)} a{" "}
            {competenciaCurta(resposta.comparacao.ate)}: {resposta.comparacao.motivo ?? "a população da base não é comparável de um ano para o outro nesta janela"}.
            A variação é calculada {textoDosTrechos(resposta.comparacao.trechos)}.</span>}
          {resposta.comparacao.estado === "comparavel" && <span data-testid="detector-comparacao" data-estado="comparavel">
            {" "}Os sinais comparados em 2 anos (8 a 10) usam a variação de {competenciaCurta(resposta.comparacao.de)} a{" "}
            {competenciaCurta(resposta.comparacao.ate)}.</span>}
          {resposta.comparacao.estado === "indisponivel" && <span data-testid="detector-comparacao" data-estado="indisponivel">
            {" "}Os sinais comparados em 2 anos (8 a 10) não estão disponíveis nesta base. {resposta.comparacao.motivo ?? indisponiveis.disponibilidade ?? ""}</span>}
          {resposta.comparacao.estado !== "comparavel" && resposta.comparacao.estado !== "comparacao_nao_habilitada" &&
            resposta.comparacao.estado !== "indisponivel" &&
            <span data-testid="detector-comparacao" data-estado={resposta.comparacao.estado}>{" "}Os sinais comparados em 2 anos (8 a 10) não são avaliados
              nesta data: falta o registro de dois anos antes.</span>}
        </caption>
        <thead><tr>
          <th scope="col" aria-sort={ordem === "nome" ? "ascending" : undefined}>{cabecaDeOrdem("Território", "nome", "detector-ordem-nome")}</th>
          <th scope="col"><span className="ferramenta-th-com-entenda"><span className="ferramenta-th-rotulo">Sinal</span>
            <Entenda sobre="Sinal" texto={daLista.sinal.texto} exemplo={daLista.sinal.exemplo} testid="detector-entenda-sinal"
              completaHref={linkDaFicha(BASE, "detector", SECOES_DAS_FICHAS.detector.sinal)}/></span></th>
          <th scope="col" aria-sort={ordem === "nivel" ? "descending" : undefined}><span className="ferramenta-th-com-entenda">
            {cabecaDeOrdem("Alerta", "nivel", "detector-ordem-nivel")}
            <Entenda sobre="Alerta" texto={daLista.alerta.texto} exemplo={daLista.alerta.exemplo} testid="detector-entenda-alerta"
              completaHref={linkDaFicha(BASE, "detector", SECOES_DAS_FICHAS.detector.alerta)}/></span></th>
          <th scope="col"><span className="ferramenta-th-com-entenda"><span className="ferramenta-th-rotulo">Por quê</span>
            <Entenda sobre="Por quê" texto={daLista.porQue.texto} exemplo={daLista.porQue.exemplo} testid="detector-entenda-por-que"
              completaHref={linkDaFicha(BASE, "detector", SECOES_DAS_FICHAS.detector.porQue)}/></span></th>
          <th scope="col" aria-sort={ordem === "numero" ? "ascending" : undefined}><span className="ferramenta-th-com-entenda">
            {cabecaDeOrdem("Último registro", "numero", "detector-ordem-numero")}
            <Entenda sobre="Último registro" texto={daLista.ultimo.texto} exemplo={daLista.ultimo.exemplo || null} testid="detector-entenda-ultimo"
              completaHref={linkDaFicha(BASE, "detector", SECOES_DAS_FICHAS.detector.ultimo)}/></span></th>
        </tr></thead>
        {naPagina.map(linha => {
          const registro = textoDoRegistro(linha), tipo = tipoDoTerritorio(linha, r);
          const detalhe = detalhes[linha.id], expandida = aberto === linha.id;
          const sinais = linhasDoTerritorio(linha, detalhe && !("erro" in detalhe) ? detalhe : null, r);
          const mesmaQueda = textoDaMesmaQueda(linha, r);
          const altura = sinais.length + (mesmaQueda ? 1 : 0);
          // O território: um grupo de linhas, uma por sinal com nível, do mais grave ao menos grave (AJ-04). O nome, o tipo e o
          // último registro aparecem uma vez para o conjunto das linhas; os contadores, os filtros, a ordem e as páginas são por
          // território.
          return <tbody key={linha.id} data-testid="detector-linha" data-id={linha.id} data-tipo={linha.tipo} data-alerta={estadoDoAlerta(linha)}
            data-sinais={linha.alerta.sinais.map(item => item.sinal).join(" ")} data-registro={registro.marca} data-linhas-de-sinal={sinais.length}
            className="ferramenta-territorio-grupo">
            {sinais.map((item, indice) => <tr key={item.sinal ?? "sem-sinal"} data-testid="detector-sinal-linha" data-sinal={item.sinal ?? ""}
              data-nivel={item.nivel ?? ""} className={indice ? "ferramenta-linha-seguinte" : undefined}>
              {indice === 0 && <th scope="rowgroup" rowSpan={altura} data-rotulo="Território" className="ferramenta-territorio">
                <button type="button" data-testid="detector-abrir" className="ferramenta-abrir" aria-expanded={expandida}
                  aria-label={(expandida ? "Fechar os detalhes de " : "Ver os detalhes de ") + linha.rotulo}
                  onClick={() => setAberto(atual => atual === linha.id ? null : linha.id)}>
                  {expandida ? <ChevronDown size={15} aria-hidden="true"/> : <ChevronRight size={15} aria-hidden="true"/>}
                  <span>{linha.rotulo}</span></button>
                {tipo && <span className="ferramenta-apoio">{tipo}</span>}
              </th>}
              <td data-rotulo="Sinal" data-testid="detector-sinal" className="ferramenta-coluna-sinal">{item.nome ?? ""}</td>
              <td data-rotulo="Alerta" data-testid="detector-alerta" data-estado={item.estado}>
                {item.nivel ? <><Nivel nivel={item.nivel}/><span data-testid="detector-criterio" className="ferramenta-apoio ferramenta-criterio-tipo">
                  {item.criterio}</span></> : <span className="ferramenta-sem-nivel">{item.texto}</span>}
              </td>
              <td data-rotulo="Por quê" data-testid="detector-por-que" data-carregando={item.porQue === null ? "true" : "false"}
                className="ferramenta-coluna-larga">{item.porQue ?? <span className="ferramenta-apoio">{detalhe && "erro" in detalhe
                  ? "A frase deste sinal está nos detalhes do território." : "Carregando a frase deste sinal…"}</span>}</td>
              {indice === 0 && <td rowSpan={altura} data-rotulo="Último registro" data-testid="detector-ultimo" className="ferramenta-coluna-ultimo">
                {textoDaUltima(linha, resposta.janela.fim, r)}
                {registro.marca !== "normal" && <span data-testid="detector-registro" data-marca={registro.marca}
                  className={"ferramenta-registro ferramenta-registro-" + registro.marca}>{registro.texto}</span>}</td>}
            </tr>)}
            {mesmaQueda && <tr data-testid="detector-linha-nota" className="ferramenta-linha-seguinte"><td colSpan={3} className="ferramenta-apoio">
              {mesmaQueda}</td></tr>}
            {expandida && <tr className="ferramenta-linha-detalhe"><td colSpan={5}>
              {!detalhe ? <p role="status" className="ferramenta-apoio"><LoaderCircle size={14} className="animate-spin inline" aria-hidden="true"/> Abrindo os detalhes…</p>
                : "erro" in detalhe ? <p role="alert" className="analise-motivo">{detalhe.erro}</p>
                  : <DetalheDoTerritorio detalhe={detalhe} linha={linha} resposta={resposta} patamar={patamarARecuperar(linha)}
                    rotulosDoPainel={p.rotulosDoPainel}
                    onAbrirNoSimulador={p.onAbrirNoSimulador ? () => p.onAbrirNoSimulador!(alvoDoSimulador(linha, resposta)) : undefined}
                    onSimularRecuperacao={p.onSimularRecuperacao && patamarARecuperar(linha) !== null
                      ? () => p.onSimularRecuperacao!(alvoDoSimulador(linha, resposta), patamarARecuperar(linha)!) : undefined}/>}
            </td></tr>}
          </tbody>;
        })}
        {!filtradas.length && <tbody><tr><td colSpan={5} data-testid="detector-sem-linhas" className="ferramenta-apoio">
          Nenhum território da seleção passa nos filtros.</td></tr></tbody>}
      </table>
    </div>}
    {resposta && paginas > 1 && <nav data-testid="detector-paginas" className="ferramenta-paginas analise-nao-imprimir" aria-label="Páginas da lista">
      <button type="button" className="analise-botao-secundario" disabled={paginaAtual === 0} onClick={() => setPagina(paginaAtual - 1)}>Anterior</button>
      <span className="ferramenta-apoio">Página {paginaAtual + 1} de {paginas} · {formatarInteiro(filtradas.length)} territórios</span>
      <button type="button" className="analise-botao-secundario" disabled={paginaAtual >= paginas - 1} onClick={() => setPagina(paginaAtual + 1)}>Próxima</button>
    </nav>}

    {/* As ressalvas de leitura (AJ-03): "raro" não quer dizer pior e o que o nível não é; a distância só como contexto; os grupos de
        cima como unidade e os conjuntos, quando estão na lista. O método está na ficha metodológica em PDF. */}
    {resposta && <ul data-testid="detector-ressalvas" className="ferramenta-notas ferramenta-ressalvas">
      {ressalvasDaLista(resposta).map(item => <li key={item.chave} data-chave={item.chave}>{item.texto}</li>)}</ul>}
  </section>;
}
