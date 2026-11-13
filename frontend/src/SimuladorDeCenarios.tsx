import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { Download, LoaderCircle, Plus, Trash2, Upload, X } from "lucide-react";
import { ErroDoMotor, pedirAoMotor, type FonteDoMotor } from "./painelApi";
import type { GrupoInfo, UnidadeDoCatalogo } from "./painelModel";
import {
  ID_DA_REFERENCIA, ID_DO_BRASIL, MAX_CENARIOS, MAX_INTERVENCOES, MAX_REFERENCIAS, MAX_TERRITORIOS, METODOS_DA_TELA, NOME_CURTO_DO_METODO, acrescentarTerritorio,
  anosDepois, cenariosEmUso, comOBrasil, comOPlanoComoIntervencao, competenciaCurta, configInicial, contasDoFinal, hipotesePertinente, metodoNaTabela, tempoDesde,
  copiarSelecao, csvDasComparacoes, csvDoSimulador, doCampoDeMes, exportarCenario, formatarMedicos, formatarPercentualInteiro, formatarTaxa, importarCenario, janelaPadrao,
  comoConjunto, mesDe, normalizarSimulador, novaIntervencao, novaReferencia, novoCenario, novoPlano, paraCampoDeMes, pedidoDoSimulador, pendenciaDoPedido, referenciasValidas,
  textoDaFaixa, textoDaHipotese, textoDoFinal, tirarTerritorio, totalDaSelecaoLocal,
  type CenarioCalculado, type CenarioDaTela, type ConfigDoSimulador, type IntervencaoDaTela, type MetodoDoCenario, type PlanejamentoDoCenario, type PlanoDaTela,
  type ReferenciaDaTela, type RespostaDoSimulador, type SelecaoDasFerramentas, type SelecaoLocal, type TerritorioSimulado,
} from "./simuladorModel";

// Simulador de Cenários Territoriais (comando V22, Eixo II, etapa 4; Docs/SIMULADOR_DE_CENARIOS.md). Quatro etapas: (1) os territórios
// em análise, numa cópia local da seleção principal, que só volta a ela por comando explícito; (2) a base histórica e o método
// (janela entre competências reais, o método padrão provisório e as alternativas, com as estatísticas históricas, só descritivas);
// (3) as intervenções e a data final; (4) as comparações e os resultados (o observado, a base do cenário, a intervenção e a faixa,
// sempre distintos), com o texto fixo de cada cenário e as exportações. Modo simples (um cenário) e modo avançado (vários). Tudo o
// que aparece é cenário hipotético condicional, calculado pelo motor (POST /api/simulador), sem o provedor de IA.
// Etapa 5 do comando: o Brasil como território (só aqui, com a contagem nacional), as referências de comparação (fixas, dinâmicas ou
// um valor informado; por quantidade ou por taxa com a população constante), o planejamento inverso (a meta é uma hipótese da
// pessoa; o resultado é uma conta condicional), a hipótese derivada da simulação (num painel à parte) e o contexto trazido pelo
// Detector de Sinais ("Abrir no Simulador" e "Simular recuperação").

type Props = {
  fonte: FonteDoMotor;
  /** A seleção principal, no contrato das ferramentas; null sem territórios. */
  principal: SelecaoDasFerramentas | null;
  resumoDaPrincipal: string;
  unidades: UnidadeDoCatalogo[];
  grupos: GrupoInfo[];
  competencias: string[];
  /** A configuração do Simulador fica guardada na área: sair e voltar não perde a seleção local nem os cenários. */
  config: ConfigDoSimulador | null;
  onConfig: (config: ConfigDoSimulador) => void;
  /** Leva a seleção local à seleção principal (comando explícito e separado). */
  onAplicarSelecao: (local: SelecaoLocal) => void;
};

const CORES = ["var(--cor-destaque)", "rgb(var(--tom-blue-600))", "rgb(var(--tom-amber-800))", "rgb(var(--tom-rose-600))", "rgb(var(--tom-slate-600))"];
const sem = (valor: string) => valor.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
function baixar(nome: string, corpo: string, tipo: string) {
  const url = URL.createObjectURL(new Blob([corpo], { type: tipo }));
  const link = document.createElement("a");
  link.href = url; link.download = nome; link.click();
  URL.revokeObjectURL(url);
}

/** O gráfico de um território: o observado (linha contínua e marcadores, só nas datas reais), a base de cada cenário (tracejada), o
 * total com a intervenção (contínua fina, na cor do cenário, com os marcadores dos eventos) e a faixa de 80% (banda), quando há. */
function GraficoDoCenario({ territorio, ultimoRegistro, cores, metrica }: { territorio: TerritorioSimulado; ultimoRegistro: string; cores: Map<string, string>;
  /** A métrica da comparação com as referências: só por quantidade a referência cabe neste gráfico de médicos. */
  metrica: string }) {
  const calculados = territorio.cenarios.filter(cenario => cenario.estado === "calculado" && cenario.trajetoria.length);
  const observados = territorio.observado.filter(ponto => ponto.valor !== null);
  if (!observados.length || !calculados.length) return <p className="ferramenta-apoio">Sem cenário calculado para desenhar.</p>;
  const largura = 760, altura = 300, esquerda = 52, direita = 16, topo = 14, base = 40;
  const inicio = mesDe(observados[0].competencia);
  const fim = Math.max(mesDe(ultimoRegistro), ...calculados.map(cenario => mesDe(cenario.trajetoria[cenario.trajetoria.length - 1].data)));
  const teto = Math.max(1, ...observados.map(ponto => ponto.valor!), ...calculados.flatMap(cenario => cenario.trajetoria.map(ponto =>
    Math.max(ponto.total, ponto.base, ponto.faixa?.superior ?? 0))));
  // As referências, por quantidade: a curva de cada uma, lida do primeiro cenário calculado (a referência é a mesma em todos). Uma
  // referência muito acima do território (mais de 3 vezes o maior valor dele) achataria as curvas: fica fora da escala, na legenda.
  const referencias = metrica !== "quantidade" ? [] : calculados[0].comparacoes.filter(comparacao => comparacao.estado === "calculada" && comparacao.pontos.length)
    .map((comparacao, indice) => ({ id: comparacao.id, marca: "R" + (indice + 1), rotulo: comparacao.rotulo, descricao: comparacao.descricao,
      final: comparacao.pontos[comparacao.pontos.length - 1].referencia,
      pontos: comparacao.pontos.map(ponto => [mesDe(ponto.data), ponto.referencia] as [number, number]) }));
  const naEscala = referencias.filter(ref => Math.max(...ref.pontos.map(ponto => ponto[1])) <= 3 * teto);
  const maximo = Math.max(teto, ...naEscala.flatMap(ref => ref.pontos.map(ponto => ponto[1]))) * 1.06;
  const x = (mes: number) => esquerda + (largura - esquerda - direita) * (fim > inicio ? (mes - inicio) / (fim - inicio) : 0.5);
  const y = (valor: number) => topo + (altura - topo - base) * (1 - valor / maximo);
  const caminho = (pontos: [number, number][]) => pontos.map(([mes, valor], indice) => (indice ? "L" : "M") + x(mes).toFixed(1) + "," + y(valor).toFixed(1)).join(" ");
  const trechosObservados: [number, number][][] = [];
  let atual: [number, number][] = [];
  for (const ponto of territorio.observado) {
    if (ponto.valor === null) { if (atual.length) trechosObservados.push(atual); atual = []; continue; }
    atual.push([mesDe(ponto.competencia), ponto.valor]);
  }
  if (atual.length) trechosObservados.push(atual);
  const anos: number[] = [];
  for (let ano = Math.ceil(inicio / 12); ano * 12 <= fim; ano++) anos.push(ano);
  const passoDosAnos = Math.max(1, Math.ceil(anos.length / 10));
  const xDoUltimo = x(mesDe(ultimoRegistro));
  const marcas: { x: number; y: number }[] = [];
  return <figure data-testid="simulador-grafico" className="ferramenta-serie ferramenta-serie-larga">
    <svg viewBox={"0 0 " + largura + " " + altura} width="100%" role="img" aria-label={"Cenários de " + territorio.rotulo +
      ": observado até " + competenciaCurta(ultimoRegistro) + "; depois, cenários hipotéticos. " + calculados.map(cenario => cenario.nome + ": " +
        formatarMedicos(cenario.final!.total) + " médicos em " + competenciaCurta(cenario.final!.data)).join("; ") +
        (referencias.length ? ". Referências: " + referencias.map(ref => ref.rotulo + ", " + formatarMedicos(ref.final) + " médicos na data final").join("; ") : "")}>
      <rect x={xDoUltimo} y={topo} width={Math.max(0, largura - direita - xDoUltimo)} height={altura - topo - base} className="ferramenta-serie-fora"/>
      <line x1={esquerda} x2={largura - direita} y1={altura - base} y2={altura - base} className="ferramenta-serie-eixo"/>
      <line x1={xDoUltimo} x2={xDoUltimo} y1={topo} y2={altura - base} className="ferramenta-serie-eixo" strokeDasharray="2 3"/>
      <text x={xDoUltimo + 4} y={topo + 11} className="ferramenta-serie-texto">simulado (hipótese)</text>
      <text x={xDoUltimo - 4} y={topo + 11} textAnchor="end" className="ferramenta-serie-texto">observado</text>
      {[0, 0.5, 1].map(parte => <text key={parte} x={esquerda - 6} y={y(maximo / 1.06 * parte) + 4} textAnchor="end" className="ferramenta-serie-texto">
        {formatarMedicos(Math.round(maximo / 1.06 * parte))}</text>)}
      {anos.filter((_, indice) => indice % passoDosAnos === 0).map(ano => <text key={ano} x={x(ano * 12)} y={altura - base + 16} textAnchor="middle"
        className="ferramenta-serie-texto">{ano}</text>)}
      {calculados.map(cenario => {
        const comFaixa = cenario.trajetoria.filter(ponto => ponto.faixa);
        if (!comFaixa.length) return null;
        const origem = mesDe(String(cenario.parametros.origem ?? ultimoRegistro)), n0 = Number(cenario.parametros.n0 ?? 0);
        const cima: [number, number][] = [[origem, n0], ...comFaixa.map(ponto => [mesDe(ponto.data), ponto.faixa!.superior] as [number, number])];
        const baixo: [number, number][] = [[origem, n0], ...comFaixa.map(ponto => [mesDe(ponto.data), ponto.faixa!.inferior] as [number, number])];
        return <path key={"f" + cenario.id} data-testid="simulador-faixa" data-cenario={cenario.id} d={caminho(cima) + " " +
          caminho([...baixo].reverse()).replace("M", "L") + " Z"} fill={cores.get(cenario.id)} fillOpacity={0.13} stroke="none"/>;
      })}
      {naEscala.map(ref => { const [mesFinal, valorFinal] = ref.pontos[ref.pontos.length - 1];
        // A marca curta ("R1") fica no fim da curva; duas marcas na mesma altura não se sobrepõem (a seguinte vai para a esquerda).
        const marca = { x: x(mesFinal) - 4, y: Math.max(topo + 24, y(valorFinal) - 5) };
        while (marcas.some(outra => Math.abs(outra.y - marca.y) < 13 && Math.abs(outra.x - marca.x) < 24)) marca.x -= 26;
        marcas.push(marca);
        return <g key={"r" + ref.id} data-testid="simulador-referencia" data-ref={ref.id}>
          <path d={caminho(ref.pontos)} className="ferramenta-serie-referencia"><title>{"Referência " + ref.rotulo + (ref.descricao ? " (" + ref.descricao + ")" : "") +
            ": " + formatarMedicos(ref.final) + " médicos na data final"}</title></path>
          <text x={marca.x} y={marca.y} textAnchor="end" className="ferramenta-serie-texto ferramenta-serie-marca">{ref.marca}</text>
        </g>; })}
      {calculados.map(cenario => {
        const origem: [number, number] = [mesDe(String(cenario.parametros.origem ?? ultimoRegistro)), Number(cenario.parametros.n0 ?? 0)];
        const cor = cores.get(cenario.id);
        const temIntervencao = cenario.trajetoria.some(ponto => ponto.intervencao !== 0);
        let anterior = 0;
        return <g key={cenario.id} data-testid="simulador-curva" data-cenario={cenario.id} data-metodo={cenario.metodo.usado ?? ""}>
          <path d={caminho([origem, ...cenario.trajetoria.map(ponto => [mesDe(ponto.data), ponto.base] as [number, number])])} fill="none" stroke={cor}
            strokeWidth={cenario.id === ID_DA_REFERENCIA ? 1.3 : 2} strokeDasharray={cenario.id === ID_DA_REFERENCIA ? "2 4" : "7 4"}/>
          {temIntervencao && <path d={caminho([origem, ...cenario.trajetoria.map(ponto => [mesDe(ponto.data), ponto.total] as [number, number])])} fill="none"
            stroke={cor} strokeWidth={1.6}/>}
          {temIntervencao && cenario.trajetoria.map(ponto => {
            const mudou = ponto.intervencao !== anterior;
            anterior = ponto.intervencao;
            return mudou ? <path key={ponto.data} data-testid="simulador-evento" d={"M" + x(mesDe(ponto.data)).toFixed(1) + "," + (y(ponto.total) - 7).toFixed(1) +
              " l5,-8 l-10,0 Z"} fill={cor}><title>{competenciaCurta(ponto.data) + ": intervenção acumulada de " + formatarMedicos(ponto.intervencao)}</title></path> : null;
          })}
        </g>;
      })}
      {trechosObservados.map((trecho, indice) => <path key={indice} d={caminho(trecho)} className="ferramenta-serie-linha"/>)}
      {observados.map(ponto => <circle key={ponto.competencia} data-testid="simulador-observado" cx={x(mesDe(ponto.competencia))} cy={y(ponto.valor!)}
        r={ponto.marca ? 4.5 : 2.6} className={"ferramenta-serie-ponto" + (ponto.marca ? " ferramenta-serie-ponto-marcado" : "")}>
        <title>{competenciaCurta(ponto.competencia) + ": " + formatarMedicos(ponto.valor!) + " (observado)" + (ponto.marca === "pico_que_volta"
          ? " · pico que volta, fora da base do cenário" : ponto.marca === "quebra_de_fonte" ? " · quebra de fonte" : "")}</title></circle>)}
    </svg>
    <figcaption className="ferramenta-legenda">
      <span><svg width="28" height="8" aria-hidden="true"><line x1="0" x2="28" y1="4" y2="4" className="ferramenta-serie-linha"/></svg>observado (registros reais)</span>
      {calculados.map(cenario => <span key={cenario.id}><svg width="28" height="8" aria-hidden="true"><line x1="0" x2="28" y1="4" y2="4"
        stroke={cores.get(cenario.id)} strokeWidth="2" strokeDasharray={cenario.id === ID_DA_REFERENCIA ? "2 4" : "7 4"}/></svg>{cenario.nome}: base do cenário
        {cenario.trajetoria.some(ponto => ponto.intervencao !== 0) ? "; linha contínua: com a intervenção (▼ nos eventos)" : ""}
        {cenario.trajetoria.some(ponto => ponto.faixa) ? "; banda: faixa de 80%" + (territorio.tipo === "conjunto" ? " (aproximação)" : "") : ""}</span>)}
      {referencias.map(ref => <span key={"r" + ref.id} data-testid="simulador-referencia-legenda" data-ref={ref.id} data-na-escala={naEscala.includes(ref) ? "true" : "false"}>
        <svg width="28" height="8" aria-hidden="true"><line x1="0" x2="28" y1="4" y2="4" className="ferramenta-serie-referencia"/></svg>{ref.marca}: referência {ref.rotulo}
        {ref.descricao ? " (" + ref.descricao + ")" : ""}{naEscala.includes(ref) ? "" : ": fora da escala deste gráfico (" + formatarMedicos(ref.final) + " médicos na data final)"}</span>)}
      {metrica !== "quantidade" && calculados[0].comparacoes.length > 0 && <span data-testid="simulador-referencia-legenda" data-na-escala="false">As referências são
        comparadas por taxa (médicos por 1.000 habitantes) e não entram neste gráfico de médicos: veja os textos de comparação.</span>}
      <span>Fonte: base do Brasil (medicina), registros de janeiro e junho até {competenciaCurta(ultimoRegistro)}.</span>
    </figcaption>
  </figure>;
}

export default function SimuladorDeCenarios(props: Props) {
  // As competências da base, em ordem (AAAAMM): os registros reais de janeiro e junho.
  const competencias = useMemo(() => props.competencias.filter(c => /^\d{6}$/.test(c)).sort(), [props.competencias]);
  const p = { ...props, competencias };
  const ultimoRegistro = competencias[competencias.length - 1] ?? "";
  const porId = useMemo(() => new Map(p.unidades.map(item => [item.id, item])), [p.unidades]);
  const nomeDe = (id: string) => { const item = porId.get(id); return item ? item.name + (item.state ? " (" + item.state + ")" : "") : id; };
  const nomeDoEstado = (prefixo: string) => { const g = p.grupos.find(item => item.id === prefixo); return g ? g.nome + (g.sigla ? " (" + g.sigla + ")" : "") : prefixo; };
  // O estado como unidade, como no resto do Agente: "Paraná (estado)", sem a sigla (um só par de parênteses).
  const estadoComoUnidade = (prefixo: string) => (p.grupos.find(item => item.id === prefixo)?.nome ?? prefixo) + " (estado)";
  const nomeDoMembro = (id: string) => id.startsWith("uf:") ? nomeDoEstado(id.slice(3)) : nomeDe(id);
  const copiaDaPrincipal = () => copiarSelecao(p.principal, { todasAsUnidades: p.unidades.filter(item => !item.selection_reason).map(item => item.id),
    unidadesDoGrupo: grupo => p.unidades.filter(item => !item.selection_reason && (item.state_code || item.id.slice(5, 7)) === grupo).map(item => item.id) });
  // A cópia local: feita ao abrir pela primeira vez. Enquanto não for alterada no Simulador, acompanha a seleção principal; depois da
  // primeira alteração aqui (ou de um cenário importado), só muda aqui dentro ou por "Copiar de novo a seleção principal".
  useEffect(() => {
    if (!ultimoRegistro) return;
    if (!p.config) { p.onConfig(configInicial(copiaDaPrincipal(), ultimoRegistro)); return; }
    if (!p.config.acompanha) return;
    const copia = copiaDaPrincipal();
    if (JSON.stringify(copia) !== JSON.stringify(p.config.local)) p.onConfig({ ...p.config, local: copia,
      referencias: referenciasValidas(p.config.referencias, copia) });
  }, [!p.config, p.config?.acompanha, p.principal, ultimoRegistro]);
  const config = p.config;
  // Vindo de "Simular recuperação" (Detector de Sinais), o Simulador abre na etapa em que a meta hipotética está à vista e é editável.
  const [etapa, setEtapa] = useState(() => props.config?.doDetector?.recuperacao && props.config.cenarios[0]?.planejamento ? 3 : 1);
  const [busca, setBusca] = useState("");
  const [buscaDeReferencia, setBuscaDeReferencia] = useState("");
  const [avisoDeReferencia, setAvisoDeReferencia] = useState<string | null>(null);
  const [avisoLocal, setAvisoLocal] = useState<string | null>(null);
  const [resposta, setResposta] = useState<RespostaDoSimulador | null>(null);
  const [calculado, setCalculado] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [foco, setFoco] = useState<string | null>(null);
  const [verValidacao, setVerValidacao] = useState(false);
  const [verComposicao, setVerComposicao] = useState(false);
  const controle = useRef<AbortController | null>(null);
  const arquivo = useRef<HTMLInputElement>(null);
  useEffect(() => () => controle.current?.abort(), []);

  const pendencia = config ? pendenciaDoPedido(config) : "Preparando o Simulador…";
  const chaveDoPedido = config && !pendencia ? p.fonte.datasetVersion + "::" + JSON.stringify(pedidoDoSimulador(config)) : "";
  const desatualizado = !!resposta && calculado !== chaveDoPedido;
  function calcular() {
    if (!config || pendencia) return;
    controle.current?.abort();
    const novo = new AbortController();
    controle.current = novo;
    const chave = chaveDoPedido;
    setCarregando(true); setErro(null);
    pedirAoMotor(p.fonte, "/api/simulador", pedidoDoSimulador(config), novo.signal)
      .then(bruto => {
        if (novo.signal.aborted) return;
        const lida = normalizarSimulador(bruto);
        setResposta(lida); setCalculado(chave); setEtapa(4);
        setFoco(atual => atual && lida.territorios.some(item => item.id === atual) ? atual : lida.territorios[0]?.id ?? null);
      })
      .catch((exc: unknown) => { if (!novo.signal.aborted) setErro(exc instanceof ErroDoMotor || exc instanceof Error ? exc.message : "Não foi possível calcular os cenários."); })
      .finally(() => { if (!novo.signal.aborted) setCarregando(false); });
  }

  const cabecalho = <header className="ferramenta-cabecalho">
    <h2 id="simulador-titulo" data-testid="simulador-titulo" tabIndex={-1} className="analise-titulo">Simulador de Cenários Territoriais</h2>
    <p className="analise-subtitulo">Cenários hipotéticos, condicionais ao método e às hipóteses que você escolher. Não são previsão, observação atual nem
      recomendação de provimento.</p>
  </header>;
  if (!config) return <section data-testid="simulador" data-estado="preparando" aria-labelledby="simulador-titulo" className="ferramenta">{cabecalho}
    <p role="status" className="analise-vazio"><LoaderCircle size={18} className="animate-spin" aria-hidden="true"/>Preparando o Simulador…</p></section>;

  const mudar = (parte: Partial<ConfigDoSimulador>) => p.onConfig({ ...config, ...parte });
  /** Uma alteração da seleção local feita no Simulador: daqui em diante, ela não acompanha mais a seleção principal. A referência
   * que apontava para um conjunto tirado daqui sai junto. */
  const mudarLocal = (local: SelecaoLocal) => mudar({ local, acompanha: false, referencias: referenciasValidas(config.referencias, local) });
  const referencias = config.referencias ?? [];
  const mudarReferencia = (id: string, parte: Partial<ReferenciaDaTela>) => mudar({ referencias: referencias.map(ref => ref.id === id ? { ...ref, ...parte } : ref) });
  function acrescentarReferencia(parte: Pick<ReferenciaDaTela, "alvo" | "rotulo" | "tipo">) {
    if (parte.tipo !== "valor" && referencias.some(ref => ref.alvo === parte.alvo)) { setAvisoDeReferencia("Esta referência já está na lista."); return; }
    const nova = novaReferencia(referencias, parte);
    if (!nova) { setAvisoDeReferencia("O Simulador compara com até " + MAX_REFERENCIAS + " referências de cada vez."); return; }
    mudar({ referencias: [...referencias, nova] });
    setAvisoDeReferencia(null); setBuscaDeReferencia("");
  }
  const mudarPlano = (indice: number, parte: Partial<PlanoDaTela>) => mudarCenario(indice, { planejamento: { ...config.cenarios[indice].planejamento!, ...parte } });
  /** "Usar como intervenção deste cenário": o acréscimo calculado pelo planejamento inverso entra nas intervenções, por comando da pessoa. */
  function usarOPlano(id: string, plano: PlanejamentoDoCenario) {
    mudar({ cenarios: config!.cenarios.map(cenario => cenario.id === id ? comOPlanoComoIntervencao(cenario, plano) : cenario) });
    setEtapa(3);
  }
  const mudarCenario = (indice: number, parte: Partial<CenarioDaTela>) => mudar({ cenarios: config.cenarios.map((cenario, k) => k === indice ? { ...cenario, ...parte } : cenario) });
  const mudarIntervencao = (indice: number, k: number, parte: Partial<IntervencaoDaTela>) => mudarCenario(indice, {
    intervencoes: config.cenarios[indice].intervencoes.map((item, n) => n === k ? { ...item, ...parte } : item) });
  const total = totalDaSelecaoLocal(config.local);
  const termo = sem(busca.trim());
  const procurar = (pedido: string) => pedido.length < 2 ? null : {
    brasil: "brasil".includes(pedido),
    estados: p.grupos.filter(g => sem(g.nome + " " + g.sigla).includes(pedido)).slice(0, 4),
    municipios: p.unidades.filter(item => !item.selection_reason && sem(item.name + " " + item.code).includes(pedido)).slice(0, 8) };
  const achados = procurar(termo);
  const achadosDeReferencia = procurar(sem(buscaDeReferencia.trim()));
  /** Os territórios da seleção local que também estão na seleção principal: só eles vão a ela (o Brasil fica só no Simulador). */
  const paraAPrincipal = total - (config.local.brasil ? 1 : 0);
  function acrescentar(alvo: { tipo: "municipio" | "estado"; id: string; grupo: string }) {
    const { local, motivo } = acrescentarTerritorio(config!.local, alvo);
    setAvisoLocal(motivo);
    if (!motivo) mudarLocal(local);
  }
  const janela = config.janela ?? resposta?.janela ?? janelaPadrao(p.competencias);
  const emUso = cenariosEmUso(config);
  const cores = new Map<string, string>([...emUso.map((cenario, indice) => [cenario.id, CORES[indice % CORES.length]] as [string, string]),
    [ID_DA_REFERENCIA, "var(--cor-texto-3)"]]);
  const territorioEmFoco = resposta?.territorios.find(item => item.id === foco) ?? resposta?.territorios[0] ?? null;

  function importar(event: ChangeEvent<HTMLInputElement>) {
    const escolhido = event.target.files?.[0];
    event.target.value = "";
    if (!escolhido) return;
    escolhido.text().then(conteudo => {
      const lido = importarCenario(conteudo);
      if (!lido.config) { setErro(lido.erro); return; }
      p.onConfig(lido.config); setResposta(null); setCalculado(""); setEtapa(1);
      setErro(null);
      setAvisoLocal("Cenário importado" + (lido.versaoDaBase && lido.versaoDaBase !== p.fonte.datasetVersion
        ? ": ele foi montado com outra versão da base; confira os territórios e calcule de novo." : ": confira e calcule."));
    });
  }

  const camposDoCenario = (cenario: CenarioDaTela, indice: number) => <div key={cenario.id} data-testid="simulador-cenario" data-id={cenario.id} className="ferramenta-cartao">
    {config.modo === "avancado" && <div className="ferramenta-cartao-cabeca">
      <span className="ferramenta-cor" style={{ background: cores.get(cenario.id) }} aria-hidden="true"/>
      <label className="analise-rotulo-campo flex-1">Nome do cenário
        <input data-testid="simulador-cenario-nome" className="analise-campo" value={cenario.nome} maxLength={80}
          onChange={event => mudarCenario(indice, { nome: event.target.value })}/></label>
      {config.cenarios.length > 1 && <button type="button" className="analise-icone" aria-label={"Remover o cenário " + cenario.nome}
        onClick={() => mudar({ cenarios: config.cenarios.filter((_, k) => k !== indice) })}><Trash2 size={14} aria-hidden="true"/></button>}
    </div>}
    <div className="ferramenta-controles">
      <label className="analise-rotulo-campo">Método da base do cenário
        <select data-testid="simulador-metodo" className="analise-campo" value={cenario.metodo}
          onChange={event => mudarCenario(indice, { metodo: event.target.value as MetodoDoCenario })}>
          {METODOS_DA_TELA.map(item => <option key={item.chave} value={item.chave}>{item.rotulo}</option>)}
        </select></label>
      {cenario.metodo === "manual" && <label className="analise-rotulo-campo">Sua taxa anual (%), como hipótese
        <input data-testid="simulador-taxa-manual" inputMode="decimal" className="analise-campo" value={cenario.taxaManual} placeholder="0,0"
          onChange={event => mudarCenario(indice, { taxaManual: event.target.value })}/></label>}
      {config.modo === "avancado" && <>
        <label className="analise-rotulo-campo">Janela própria: de
          <select data-testid="simulador-cenario-janela-inicio" className="analise-campo" value={cenario.janela?.inicio ?? ""}
            onChange={event => mudarCenario(indice, { janela: event.target.value ? { inicio: event.target.value, fim: cenario.janela?.fim ?? janela?.fim ?? ultimoRegistro } : null })}>
            <option value="">a janela geral</option>
            {p.competencias.slice(0, -1).map(c => <option key={c} value={c}>{competenciaCurta(c)}</option>)}
          </select></label>
        {cenario.janela && <label className="analise-rotulo-campo">até
          <select data-testid="simulador-cenario-janela-fim" className="analise-campo" value={cenario.janela.fim}
            onChange={event => mudarCenario(indice, { janela: { inicio: cenario.janela!.inicio, fim: event.target.value } })}>
            {p.competencias.filter(c => c > cenario.janela!.inicio).map(c => <option key={c} value={c}>{competenciaCurta(c)}</option>)}
          </select></label>}
      </>}
    </div>
    <p className="ferramenta-apoio">{METODOS_DA_TELA.find(item => item.chave === cenario.metodo)?.apoio}.</p>
  </div>;

  // O planejamento inverso de um cenário: a meta hipotética (um número de médicos, o patamar anterior ou uma referência) e o calendário
  // dos acréscimos. O motor devolve o menor número inteiro de médicos por evento que alcança a meta na data final.
  const planoDo = (cenario: CenarioDaTela, indice: number) => { const plano = cenario.planejamento;
    return <div data-testid="simulador-plano" data-ativo={plano ? "true" : "false"} data-meta={plano?.meta ?? ""} className="ferramenta-plano">
      {!plano ? <button type="button" data-testid="simulador-plano-novo" className="analise-botao-secundario"
        onClick={() => mudarCenario(indice, { planejamento: novoPlano(anosDepois(ultimoRegistro, 1)) })}>
        <Plus size={14} aria-hidden="true"/>Calcular o acréscimo que alcança uma meta (planejamento inverso)</button> : <>
        <p className="ferramenta-cartao-titulo">Planejamento inverso: meta hipotética</p>
        <p className="ferramenta-apoio">O Simulador calcula o menor número inteiro de médicos por evento com que este cenário alcança a meta na data final. A meta é
          uma hipótese sua, e você pode trocá-la: o resultado é uma conta condicional às hipóteses do cenário, não um plano.{total > 1 && " Com mais de um " +
            "território, a conta é feita para cada um."}</p>
        <div className="ferramenta-intervencao">
          <label className="analise-rotulo-campo">Meta hipotética
            <select data-testid="simulador-plano-meta" className="analise-campo" value={plano.meta}
              onChange={event => mudarPlano(indice, { meta: event.target.value as PlanoDaTela["meta"],
                ...(event.target.value === "referencia" && !referencias.some(ref => ref.id === plano.referencia) ? { referencia: referencias[0]?.id ?? "" } : {}) })}>
              <option value="valor">Chegar a um número de médicos</option>
              <option value="patamar">Voltar ao patamar anterior</option>
              <option value="referencia" disabled={!referencias.length}>Alcançar uma referência{referencias.length ? "" : " (acrescente uma na etapa 1)"}</option>
            </select></label>
          {plano.meta !== "referencia" && <label className="analise-rotulo-campo">{plano.meta === "valor" ? "Médicos na data final" : "Patamar, em médicos"}
            <input data-testid="simulador-plano-valor" inputMode="decimal" className="analise-campo" value={plano.valor}
              placeholder={plano.meta === "patamar" ? "em branco: o patamar anterior de cada território" : "por exemplo, 30"}
              title={plano.meta === "patamar" ? "O patamar anterior é a maior média de dois anos seguidos antes dos registros mais recentes; em branco, vale o de cada território" : undefined}
              onChange={event => mudarPlano(indice, { valor: event.target.value })}/></label>}
          {plano.meta === "referencia" && <label className="analise-rotulo-campo">Referência da meta
            <select data-testid="simulador-plano-referencia" className="analise-campo" value={plano.referencia}
              onChange={event => mudarPlano(indice, { referencia: event.target.value })}>
              {!referencias.some(ref => ref.id === plano.referencia) && <option value="">escolha a referência</option>}
              {referencias.map(ref => <option key={ref.id} value={ref.id}>{ref.rotulo}</option>)}
            </select></label>}
          <label className="analise-rotulo-campo">{plano.periodica ? "Primeiro acréscimo em" : "Acréscimo em"}
            <input type="month" data-testid="simulador-plano-em" className="analise-campo" value={paraCampoDeMes(plano.em)} min={paraCampoDeMes(anosDepois(ultimoRegistro, 0))}
              onChange={event => mudarPlano(indice, { em: doCampoDeMes(event.target.value) })}/></label>
          <label className="analise-caixa ferramenta-caixa"><input type="checkbox" data-testid="simulador-plano-periodica" checked={plano.periodica}
            onChange={event => mudarPlano(indice, { periodica: event.target.checked, ate: event.target.checked && plano.ate <= plano.em ? anosDepois(plano.em || ultimoRegistro, 2) : plano.ate })}/>
            <span>Repetir</span></label>
          {plano.periodica && <>
            <label className="analise-rotulo-campo">a cada (meses)
              <input data-testid="simulador-plano-passo" inputMode="numeric" className="analise-campo" value={plano.aCadaMeses}
                onChange={event => mudarPlano(indice, { aCadaMeses: event.target.value })}/></label>
            <label className="analise-rotulo-campo">até
              <input type="month" data-testid="simulador-plano-ate" className="analise-campo" value={paraCampoDeMes(plano.ate)}
                onChange={event => mudarPlano(indice, { ate: doCampoDeMes(event.target.value) })}/></label>
          </>}
          <label className="analise-rotulo-campo">Permanência (% ao ano)
            <input data-testid="simulador-plano-permanencia" inputMode="decimal" className="analise-campo" value={plano.permanencia}
              title="100 = todos permanecem (hipótese padrão)" onChange={event => mudarPlano(indice, { permanencia: event.target.value })}/></label>
          <button type="button" data-testid="simulador-plano-remover" className="analise-icone" aria-label="Remover o planejamento inverso"
            onClick={() => mudar({ cenarios: config.cenarios.map((item, k) => { if (k !== indice) return item; const { planejamento: _plano, ...resto } = item; return resto; }) })}>
            <Trash2 size={14} aria-hidden="true"/></button>
        </div>
      </>}
    </div>; };

  const intervencoesDo = (cenario: CenarioDaTela, indice: number) => <div key={cenario.id} data-testid="simulador-intervencoes" data-id={cenario.id} className="ferramenta-cartao">
    {config.modo === "avancado" && <p className="ferramenta-cartao-titulo"><span className="ferramenta-cor" style={{ background: cores.get(cenario.id) }} aria-hidden="true"/>{cenario.nome}</p>}
    {!cenario.intervencoes.length && <p className="ferramenta-apoio">Sem intervenção: só a base do cenário.</p>}
    {cenario.intervencoes.map((item, k) => <div key={k} data-testid="simulador-intervencao" className="ferramenta-intervencao">
      <label className="analise-rotulo-campo">Tipo
        <select data-testid="simulador-intervencao-tipo" className="analise-campo" value={item.tipo}
          onChange={event => mudarIntervencao(indice, k, { tipo: event.target.value as IntervencaoDaTela["tipo"] })}>
          <option value="acrescimo">Acréscimo de médicos</option><option value="retirada">Retirada de médicos</option>
        </select></label>
      <label className="analise-rotulo-campo">Médicos por evento
        <input data-testid="simulador-intervencao-quantidade" inputMode="decimal" className="analise-campo" value={item.quantidade}
          onChange={event => mudarIntervencao(indice, k, { quantidade: event.target.value })}/></label>
      <label className="analise-rotulo-campo">{item.periodica ? "Primeiro evento em" : "Em"}
        <input type="month" data-testid="simulador-intervencao-em" className="analise-campo" value={paraCampoDeMes(item.em)} min={paraCampoDeMes(anosDepois(ultimoRegistro, 0))}
          onChange={event => mudarIntervencao(indice, k, { em: doCampoDeMes(event.target.value) })}/></label>
      <label className="analise-caixa ferramenta-caixa"><input type="checkbox" data-testid="simulador-intervencao-periodica" checked={item.periodica}
        onChange={event => mudarIntervencao(indice, k, { periodica: event.target.checked, ate: event.target.checked && item.ate <= item.em ? anosDepois(item.em || ultimoRegistro, 2) : item.ate })}/>
        <span>Repetir</span></label>
      {item.periodica && <>
        <label className="analise-rotulo-campo">a cada (meses)
          <input data-testid="simulador-intervencao-passo" inputMode="numeric" className="analise-campo" value={item.aCadaMeses}
            onChange={event => mudarIntervencao(indice, k, { aCadaMeses: event.target.value })}/></label>
        <label className="analise-rotulo-campo">até
          <input type="month" data-testid="simulador-intervencao-ate" className="analise-campo" value={paraCampoDeMes(item.ate)}
            onChange={event => mudarIntervencao(indice, k, { ate: doCampoDeMes(event.target.value) })}/></label>
      </>}
      <label className="analise-rotulo-campo">Permanência (% ao ano)
        <input data-testid="simulador-intervencao-permanencia" inputMode="decimal" className="analise-campo" value={item.permanencia}
          title="100 = todos permanecem (hipótese padrão)" onChange={event => mudarIntervencao(indice, k, { permanencia: event.target.value })}/></label>
      <button type="button" className="analise-icone" aria-label="Remover a intervenção"
        onClick={() => mudarCenario(indice, { intervencoes: cenario.intervencoes.filter((_, n) => n !== k) })}><Trash2 size={14} aria-hidden="true"/></button>
    </div>)}
    <button type="button" data-testid="simulador-intervencao-nova" className="analise-botao-secundario" disabled={cenario.intervencoes.length >= MAX_INTERVENCOES}
      onClick={() => mudarCenario(indice, { intervencoes: [...cenario.intervencoes, novaIntervencao(anosDepois(ultimoRegistro, 1))] })}>
      <Plus size={14} aria-hidden="true"/>Acrescentar intervenção</button>
    {planoDo(cenario, indice)}
  </div>;

  const cenarioDaTabela = (cenario: CenarioCalculado, conjunto: boolean) => <td key={cenario.id} data-testid="simulador-final" data-cenario={cenario.id}
    data-estado={cenario.estado} title={cenario.motivo ?? cenario.texto ?? undefined}>{textoDoFinal(cenario, conjunto)}
    {cenario.estado === "calculado" && cenario.metodo.usado && <span data-testid="simulador-metodo-usado" className="ferramenta-apoio block"
      title={"Método " + cenario.metodo.usado}>{metodoNaTabela(cenario, conjunto)}</span>}</td>;

  return <section data-testid="simulador" data-estado={carregando ? "carregando" : erro ? "erro" : resposta ? (desatualizado ? "desatualizado" : "pronto") : "configurando"}
    data-etapa={etapa} data-modo={config.modo} aria-labelledby="simulador-titulo" aria-busy={carregando || undefined} className="ferramenta">
    {cabecalho}
    <p data-testid="simulador-data" role="note" className="ferramenta-aviso">O registro mais recente da base é <strong>{competenciaCurta(ultimoRegistro)}</strong>{" "}
      <span data-testid="simulador-distancia">(há {tempoDesde(ultimoRegistro, new Date())})</span>: é histórico. Tudo o que vem depois dele é <strong>simulado</strong>, nunca
      observado; as datas simuladas, mesmo as que já passaram, não descrevem a situação de hoje.</p>
    {config.doDetector && <p data-testid="simulador-do-detector" data-recuperacao={config.doDetector.recuperacao ? "true" : "false"} role="note" className="ferramenta-aviso">
      Aberto pelo <strong>Detector de Sinais</strong>: {config.doDetector.rotulo}, avaliado em {competenciaCurta(config.doDetector.fim)}
      {config.doDetector.exploratorio ? ", com parâmetros personalizados (exploratórios)" : ""}. {config.doDetector.sinais.length
        ? "Sinais à vista lá: " + config.doDetector.sinais.join("; ") + "." : "Sem sinais à vista lá."} Os sinais descrevem registros reais; aqui, o que vem
      depois do último registro é cenário hipotético.{config.doDetector.recuperacao && " “Simular recuperação” trouxe, como meta hipotética que você pode " +
        "trocar, a volta ao patamar anterior (etapa 3)."}{" "}
      <button type="button" data-testid="simulador-do-detector-dispensar" className="analise-link analise-nao-imprimir" onClick={() => mudar({ doDetector: undefined })}>
        Dispensar este aviso</button></p>}
    <div className="ferramenta-acoes analise-nao-imprimir">
      <div role="group" aria-label="Modo do Simulador" className="ferramenta-modos">
        <button type="button" data-testid="simulador-modo-simples" className="analise-botao-secundario" aria-pressed={config.modo === "simples"}
          onClick={() => mudar({ modo: "simples" })}>Modo simples</button>
        <button type="button" data-testid="simulador-modo-avancado" className="analise-botao-secundario" aria-pressed={config.modo === "avancado"}
          onClick={() => mudar({ modo: "avancado" })}>Modo avançado</button>
      </div>
      <button type="button" data-testid="simulador-exportar-cenario" className="analise-botao-secundario"
        onClick={() => baixar("cenario_do_simulador.json", exportarCenario(config, { versaoDoMetodo: resposta?.versao ?? "", versaoDaBase: p.fonte.datasetVersion,
          ultimoRegistro, quando: new Date().toISOString() }), "application/json")}><Download size={14} aria-hidden="true"/>Exportar o cenário (JSON)</button>
      <button type="button" data-testid="simulador-importar-cenario" className="analise-botao-secundario" onClick={() => arquivo.current?.click()}>
        <Upload size={14} aria-hidden="true"/>Importar cenário (JSON)</button>
      <input ref={arquivo} type="file" accept="application/json,.json" data-testid="simulador-arquivo" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={importar}/>
    </div>

    <ol className="ferramenta-etapas analise-nao-imprimir" aria-label="Etapas do Simulador">
      {["Territórios em análise", "Base histórica e método", "Intervenções e horizonte", "Comparações e resultados"].map((nome, indice) => <li key={nome}>
        <button type="button" data-testid={"simulador-etapa-" + (indice + 1)} aria-current={etapa === indice + 1 ? "step" : undefined} className="ferramenta-etapa"
          disabled={indice === 3 && !resposta} onClick={() => setEtapa(indice + 1)}><span className="ferramenta-etapa-numero">{indice + 1}</span>{nome}</button></li>)}
    </ol>

    {etapa === 1 && <div data-testid="simulador-territorios" className="ferramenta-etapa-corpo">
      <p data-testid="simulador-origem-da-selecao" data-acompanha={config.acompanha ? "true" : "false"} className="ferramenta-apoio">{config.acompanha
        ? <>Esta é uma <strong>cópia</strong> da seleção principal ({p.resumoDaPrincipal}). O que você acrescentar ou tirar aqui vale só no Simulador;
          a seleção principal só muda com “Aplicar à seleção principal”.</>
        : config.doDetector ? <>Esta seleção veio do <strong>Detector de Sinais</strong> e vale só no Simulador: não acompanha a seleção principal
          ({p.resumoDaPrincipal}), que só muda com “Aplicar à seleção principal”.</>
        : <>Esta seleção é <strong>só do Simulador</strong>: foi alterada aqui e não acompanha mais a seleção principal ({p.resumoDaPrincipal}), que só
          muda com “Aplicar à seleção principal”.</>}</p>
      {total > MAX_TERRITORIOS && <p data-testid="simulador-muitos" role="status" className="analise-motivo">A seleção local tem {total.toLocaleString("pt-BR")} territórios, e o
        Simulador compara até {MAX_TERRITORIOS} de cada vez: tire territórios daqui (a seleção principal não muda).{" "}
        <button type="button" data-testid="simulador-esvaziar" className="analise-link" onClick={() => mudarLocal({ municipios: [], estados: [], conjuntos: [] })}>
          Esvaziar a seleção local</button></p>}
      <ul data-testid="simulador-locais" data-total={total} className="analise-selecionado-unidades" aria-label="Territórios do Simulador">
        {config.local.brasil && <li data-testid="simulador-local" data-id={ID_DO_BRASIL} className="analise-etiqueta"
          title="A contagem nacional de médicos únicos; não é a soma dos estados nem dos municípios">Brasil (contagem nacional)
          <button type="button" className="analise-icone analise-icone-pequeno" aria-label="Tirar o Brasil do Simulador"
            onClick={() => mudarLocal(tirarTerritorio(config.local, ID_DO_BRASIL))}><X size={13} aria-hidden="true"/></button></li>}
        {config.local.estados.map(prefixo => <li key={"uf:" + prefixo} data-testid="simulador-local" data-id={"uf:" + prefixo} className="analise-etiqueta">
          {estadoComoUnidade(prefixo)}<button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + nomeDoEstado(prefixo) + " do Simulador"}
            onClick={() => mudarLocal(tirarTerritorio(config.local, "uf:" + prefixo))}><X size={13} aria-hidden="true"/></button></li>)}
        {config.local.conjuntos.map(conjunto => <li key={conjunto.id} data-testid="simulador-local" data-id={conjunto.id} className="analise-etiqueta"
          title={conjunto.rotulo + ": " + conjunto.membros.map(id => id.startsWith("uf:") ? nomeDoEstado(id.slice(3)) : nomeDe(id)).join(", ")}>
          {conjunto.rotulo} (conjunto de {conjunto.membros.length})<button type="button" className="analise-icone analise-icone-pequeno"
            aria-label={"Tirar o conjunto " + conjunto.rotulo + " do Simulador"} onClick={() => mudarLocal(tirarTerritorio(config.local, conjunto.id))}>
            <X size={13} aria-hidden="true"/></button></li>)}
        {config.local.municipios.slice(0, 150).map(id => <li key={id} data-testid="simulador-local" data-id={id} className="analise-etiqueta">{nomeDe(id)}
          <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + nomeDe(id) + " do Simulador"}
            onClick={() => mudarLocal(tirarTerritorio(config.local, id))}><X size={13} aria-hidden="true"/></button></li>)}
        {config.local.municipios.length > 150 && <li className="ferramenta-apoio">e mais {(config.local.municipios.length - 150).toLocaleString("pt-BR")} municípios</li>}
        {!total && <li className="ferramenta-apoio">Nenhum território no Simulador: busque abaixo ou copie a seleção principal.</li>}
      </ul>
      {config.local.conjuntos.length > 0 && <div className="ferramenta-metodo">
        <button type="button" data-testid="simulador-composicao-botao" className="analise-link" aria-expanded={verComposicao} onClick={() => setVerComposicao(valor => !valor)}>
          {verComposicao ? "Fechar a composição dos conjuntos" : "Ver a composição dos conjuntos (" + config.local.conjuntos.length + ")"}</button>
        {verComposicao && <ul data-testid="simulador-composicao" className="ferramenta-notas">
          {config.local.conjuntos.map(conjunto => <li key={conjunto.id} data-id={conjunto.id}><strong>{conjunto.rotulo}</strong>{conjunto.versao ? " (versão " + conjunto.versao + ")" : ""}:{" "}
            {conjunto.membros.map(nomeDoMembro).join(", ")}.</li>)}
          <li>O valor de um conjunto é a soma das contagens dos componentes, não o número de médicos diferentes.</li>
        </ul>}
      </div>}
      <label className="analise-rotulo-campo ferramenta-busca">Acrescentar um território (município, estado ou o Brasil), só no Simulador
        <input type="search" data-testid="simulador-busca" className="analise-campo" value={busca} autoComplete="off" placeholder="Digite o nome"
          onChange={event => { setBusca(event.target.value); setAvisoLocal(null); }}/></label>
      {achados && <ul data-testid="simulador-achados" className="ferramenta-achados">
        {achados.brasil && <li key="br"><button type="button" data-testid="simulador-acrescentar" data-id={ID_DO_BRASIL} className="analise-botao-secundario"
          onClick={() => { if (config.local.brasil) setAvisoLocal("O Brasil já está na seleção do Simulador."); else { setAvisoLocal(null); mudarLocal(comOBrasil(config.local, true)); } }}>
          <Plus size={13} aria-hidden="true"/>Brasil (contagem nacional de médicos únicos)</button></li>}
        {achados.estados.map(g => <li key={"uf" + g.id}><button type="button" data-testid="simulador-acrescentar" data-id={"uf:" + g.id} className="analise-botao-secundario"
          onClick={() => acrescentar({ tipo: "estado", id: g.id, grupo: g.id })}><Plus size={13} aria-hidden="true"/>{g.nome} como estado (unidade)</button></li>)}
        {achados.municipios.map(item => <li key={item.id}><button type="button" data-testid="simulador-acrescentar" data-id={item.id} className="analise-botao-secundario"
          onClick={() => acrescentar({ tipo: "municipio", id: item.id, grupo: item.state_code || item.id.slice(5, 7) })}><Plus size={13} aria-hidden="true"/>{nomeDe(item.id)}</button></li>)}
        {!achados.brasil && !achados.estados.length && !achados.municipios.length && <li className="ferramenta-apoio">Nada encontrado com “{busca.trim()}”.</li>}
      </ul>}
      {avisoLocal && <p data-testid="simulador-aviso-local" role="status" className="ferramenta-apoio">{avisoLocal}</p>}
      {!config.acompanha && <p data-testid="simulador-nao-acompanha" role="status" className="ferramenta-exploratorio">{config.doDetector
        ? <>A seleção aberta pelo Detector de Sinais <strong>não acompanha</strong> a seleção principal: o que mudar na Seleção de Territórios não chega ao
          Simulador. “Copiar de novo a seleção principal” traz a seleção principal de volta, e a cópia volta a acompanhá-la.</>
        : <>A cópia <strong>deixou de acompanhar</strong> a seleção principal depois da alteração feita aqui: o que mudar na Seleção de Territórios não chega
          mais ao Simulador. “Copiar de novo a seleção principal” traz a seleção principal de volta, e a cópia volta a acompanhá-la.</>}</p>}
      <div data-testid="simulador-referencias" data-total={referencias.length} data-metrica={config.metrica ?? "quantidade"} className="ferramenta-cartao">
        <p className="ferramenta-cartao-titulo">Referências de comparação (opcional)</p>
        <p className="ferramenta-apoio">Uma referência é um território, ou um valor seu, com que cada cenário é comparado. Ela pode ficar fora da seleção do
          Simulador e não muda a seleção principal. <strong>Fixa</strong>: o último valor registrado se mantém. <strong>Dinâmica</strong>: segue o método padrão
          provisório dela, sem intervenções.</p>
        {referencias.length > 0 && <ul data-testid="simulador-referencias-lista" className="ferramenta-referencias" aria-label="Referências de comparação">
          {referencias.map(ref => <li key={ref.id} data-testid="simulador-referencia-item" data-id={ref.id} data-alvo={ref.alvo} data-tipo={ref.tipo}
            className="ferramenta-referencia">
            <span className="ferramenta-referencia-nome">{ref.rotulo}</span>
            {ref.tipo === "valor" ? <label className="analise-rotulo-campo">{config.metrica === "taxa" ? "Valor (médicos por 1.000 habitantes)" : "Valor (médicos)"}
              <input data-testid="simulador-referencia-valor" inputMode="decimal" className="analise-campo" value={ref.valor}
                onChange={event => mudarReferencia(ref.id, { valor: event.target.value })}/></label>
              : <label className="analise-rotulo-campo">Como evolui
                <select data-testid="simulador-referencia-tipo" className="analise-campo" value={ref.tipo}
                  onChange={event => mudarReferencia(ref.id, { tipo: event.target.value as ReferenciaDaTela["tipo"] })}>
                  <option value="fixa">Fixa: o último valor se mantém</option><option value="dinamica">Dinâmica: segue o método padrão</option>
                </select></label>}
            <button type="button" className="analise-icone" aria-label={"Tirar a referência " + ref.rotulo}
              onClick={() => mudar({ referencias: referencias.filter(item => item.id !== ref.id) })}><Trash2 size={14} aria-hidden="true"/></button>
          </li>)}
        </ul>}
        <label className="analise-rotulo-campo ferramenta-busca">Acrescentar uma referência (município ou estado)
          <input type="search" data-testid="simulador-referencia-busca" className="analise-campo" value={buscaDeReferencia} autoComplete="off" placeholder="Digite o nome"
            disabled={referencias.length >= MAX_REFERENCIAS} onChange={event => { setBuscaDeReferencia(event.target.value); setAvisoDeReferencia(null); }}/></label>
        {achadosDeReferencia && <ul data-testid="simulador-referencia-achados" className="ferramenta-achados">
          {achadosDeReferencia.estados.map(g => <li key={"uf" + g.id}><button type="button" data-testid="simulador-referencia-acrescentar" data-id={"uf:" + g.id}
            className="analise-botao-secundario" onClick={() => acrescentarReferencia({ alvo: "uf:" + g.id, rotulo: estadoComoUnidade(g.id), tipo: "fixa" })}>
            <Plus size={13} aria-hidden="true"/>{g.nome} (estado)</button></li>)}
          {achadosDeReferencia.municipios.map(item => <li key={item.id}><button type="button" data-testid="simulador-referencia-acrescentar" data-id={item.id}
            className="analise-botao-secundario" onClick={() => acrescentarReferencia({ alvo: item.id, rotulo: nomeDe(item.id), tipo: "fixa" })}>
            <Plus size={13} aria-hidden="true"/>{nomeDe(item.id)}</button></li>)}
          {!achadosDeReferencia.estados.length && !achadosDeReferencia.municipios.length && <li className="ferramenta-apoio">Nada encontrado com “{buscaDeReferencia.trim()}”.</li>}
        </ul>}
        <div className="ferramenta-detalhe-acoes">
          <button type="button" data-testid="simulador-referencia-brasil" className="analise-botao-secundario" disabled={referencias.length >= MAX_REFERENCIAS}
            onClick={() => acrescentarReferencia({ alvo: ID_DO_BRASIL, rotulo: "Brasil", tipo: "fixa" })}><Plus size={13} aria-hidden="true"/>Brasil</button>
          {config.local.conjuntos.map(conjunto => <button key={conjunto.id} type="button" data-testid="simulador-referencia-conjunto" data-id={conjunto.id}
            className="analise-botao-secundario" disabled={referencias.length >= MAX_REFERENCIAS}
            onClick={() => acrescentarReferencia({ alvo: conjunto.id, rotulo: comoConjunto(conjunto.rotulo), tipo: "fixa" })}>
            <Plus size={13} aria-hidden="true"/>{comoConjunto(conjunto.rotulo)}</button>)}
          <button type="button" data-testid="simulador-referencia-valor-nova" className="analise-botao-secundario" disabled={referencias.length >= MAX_REFERENCIAS}
            onClick={() => acrescentarReferencia({ alvo: "valor", rotulo: "Valor informado por você", tipo: "valor" })}><Plus size={13} aria-hidden="true"/>Um valor seu</button>
        </div>
        {avisoDeReferencia && <p data-testid="simulador-referencia-aviso" role="status" className="ferramenta-apoio">{avisoDeReferencia}</p>}
        {referencias.length > 0 && <>
          <label className="analise-rotulo-campo ferramenta-busca">Comparar por
            <select data-testid="simulador-metrica" className="analise-campo" value={config.metrica ?? "quantidade"}
              onChange={event => mudar({ metrica: event.target.value === "taxa" ? "taxa" : "quantidade" })}>
              <option value="quantidade">Quantidade de médicos</option>
              <option value="taxa">Taxa por 1.000 habitantes, com a população constante</option>
            </select></label>
          <p data-testid="simulador-metrica-apoio" className="ferramenta-apoio">{config.metrica === "taxa"
            ? "Hipótese: a população do último registro (" + competenciaCurta(ultimoRegistro) + ") vale em todas as datas simuladas; a base não traz população " +
              "futura. Um valor seu é lido como taxa."
            : "Comparar a quantidade de médicos de territórios de portes diferentes não é comparar a suficiência do atendimento."} A comparação mostra a
            diferença, a razão e o índice (100 é a referência); uma referência que contém o território, ou é parte dele, leva o aviso de sobreposição.</p>
        </>}
      </div>
      <div className="ferramenta-detalhe-acoes">
        <button type="button" data-testid="simulador-copiar-principal" className="analise-botao-secundario" disabled={!p.principal}
          onClick={() => { const copia = copiaDaPrincipal(); mudar({ local: copia, acompanha: true, doDetector: undefined, referencias: referenciasValidas(config.referencias, copia) });
            setAvisoLocal("Seleção principal copiada de novo."); }}>Copiar de novo a seleção principal</button>
        <button type="button" data-testid="simulador-aplicar-principal" className="analise-botao-secundario" disabled={!paraAPrincipal}
          title="Leva estes territórios à Seleção de Territórios; pode ser desfeito pelo Desfazer" onClick={() => { p.onAplicarSelecao(config.local);
            setAvisoLocal("A seleção do Simulador foi aplicada à seleção principal." + (config.local.brasil ? " O Brasil fica só no Simulador: a seleção principal " +
              "não o tem como unidade." : "")); }}>Aplicar à seleção principal</button>
        <button type="button" data-testid="simulador-avancar-1" className="analise-botao-primario" disabled={!total || total > MAX_TERRITORIOS} onClick={() => setEtapa(2)}>Seguir: base histórica e método</button>
      </div>
    </div>}

    {etapa === 2 && <div data-testid="simulador-base" className="ferramenta-etapa-corpo">
      <div className="ferramenta-controles">
        <label className="analise-rotulo-campo">Janela histórica: de
          <select data-testid="simulador-janela-inicio" className="analise-campo" value={janela?.inicio ?? ""}
            onChange={event => mudar({ janela: { inicio: event.target.value, fim: janela?.fim ?? ultimoRegistro } })}>
            {p.competencias.filter(c => !janela || c < janela.fim).map(c => <option key={c} value={c}>{competenciaCurta(c)}</option>)}
          </select></label>
        <label className="analise-rotulo-campo">até (a origem do cenário)
          <select data-testid="simulador-janela-fim" className="analise-campo" value={janela?.fim ?? ""}
            onChange={event => mudar({ janela: { inicio: janela?.inicio ?? p.competencias[0], fim: event.target.value } })}>
            {p.competencias.filter(c => !janela || c > janela.inicio).map(c => <option key={c} value={c}>{competenciaCurta(c)}</option>)}
          </select></label>
        <div role="group" aria-label="Atalhos da janela" className="ferramenta-atalhos">
          <button type="button" data-testid="simulador-janela-padrao" className="analise-botao-secundario" disabled={!config.janela}
            onClick={() => mudar({ janela: null })}>Janela padrão (3 anos)</button>
          <button type="button" data-testid="simulador-janela-5-anos" className="analise-botao-secundario" disabled={p.competencias.length < 11}
            onClick={() => mudar({ janela: { inicio: p.competencias[Math.max(0, p.competencias.length - 11)], fim: ultimoRegistro } })}>Últimos 5 anos</button>
          <button type="button" data-testid="simulador-janela-completa" className="analise-botao-secundario" disabled={p.competencias.length < 2}
            onClick={() => mudar({ janela: { inicio: p.competencias[0], fim: ultimoRegistro } })}>Série completa</button>
        </div>
      </div>
      <p className="ferramenta-apoio">A janela usa só registros reais, de janeiro e junho (5 e 7 meses entre um e outro).{janela && " De " + competenciaCurta(janela.inicio) +
        " a " + competenciaCurta(janela.fim) + ": " + ((mesDe(janela.fim) - mesDe(janela.inicio)) / 12).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " anos."}
        {janela && janela.fim !== ultimoRegistro && " Com a origem antes do último registro, o cenário também é calculado para as datas que já têm registro, até " +
          competenciaCurta(ultimoRegistro) + ", para comparar com o observado."}</p>
      {(config.modo === "simples" ? config.cenarios.slice(0, 1) : config.cenarios).map((cenario, indice) => camposDoCenario(cenario, indice))}
      {config.modo === "avancado" && <button type="button" data-testid="simulador-cenario-novo" className="analise-botao-secundario" disabled={config.cenarios.length >= MAX_CENARIOS}
        onClick={() => { const n = config.cenarios.reduce((maior, cenario) => Math.max(maior, Number(/^c(\d+)$/.exec(cenario.id)?.[1] ?? 0)), 0) + 1;
          mudar({ cenarios: [...config.cenarios, novoCenario("c" + n, "Cenário " + n)] }); }}><Plus size={14} aria-hidden="true"/>Acrescentar cenário</button>}
      <p className="ferramenta-apoio">A persistência (M0) entra sempre como referência de comparação. Comparar métodos e janelas mostra a sensibilidade ao método e à janela, não
        uma faixa de confiança.</p>
      {!territorioEmFoco && <p data-testid="simulador-estatisticas-depois" className="ferramenta-apoio">As estatísticas históricas de cada território (registros usáveis, lacunas,
        taxas de junho a junho, taxa composta e média aritmética, esta só como descrição) aparecem aqui depois de calcular.</p>}
      {territorioEmFoco && resposta && <div data-testid="simulador-estatisticas" className="ferramenta-cartao">
        <p className="ferramenta-cartao-titulo">Estatísticas históricas de {territorioEmFoco.rotulo} (só descrição do passado)</p>
        {resposta.territorios.length > 1 && <label className="analise-rotulo-campo ferramenta-busca">Território
          <select data-testid="simulador-estatisticas-foco" className="analise-campo" value={territorioEmFoco.id} onChange={event => setFoco(event.target.value)}>
            {resposta.territorios.map(item => <option key={item.id} value={item.id}>{item.rotulo}</option>)}
          </select></label>}
        <p className="ferramenta-apoio">{territorioEmFoco.historico.registros} registros usáveis{territorioEmFoco.historico.de ? ", de " + competenciaCurta(territorioEmFoco.historico.de) + " a " +
          competenciaCurta(territorioEmFoco.historico.ate) : ""}{territorioEmFoco.lacunas.length ? "; sem registro em " + territorioEmFoco.lacunas.map(competenciaCurta).join(", ") : ""}.
          {territorioEmFoco.historico.taxasDeJunho.length > 0 && " Taxas de junho a junho: " + territorioEmFoco.historico.taxasDeJunho.map(taxa =>
            competenciaCurta(taxa.ate) + " " + formatarTaxa(taxa.taxaPct)).join("; ") + "."}</p>
        <dl className="ferramenta-numeros">
          <div><dt>Taxa composta (M1)</dt><dd data-testid="simulador-taxa-composta">{territorioEmFoco.historico.taxaCompostaPct === null ? "não definida" : formatarTaxa(territorioEmFoco.historico.taxaCompostaPct) + " ao ano"}</dd></div>
          <div><dt>Média aritmética das taxas</dt><dd data-testid="simulador-media-aritmetica">{territorioEmFoco.historico.mediaAritmeticaPct === null ? "—" : formatarTaxa(territorioEmFoco.historico.mediaAritmeticaPct)}</dd></div>
          <div><dt>Mediana das taxas</dt><dd>{territorioEmFoco.historico.medianaPct === null ? "—" : formatarTaxa(territorioEmFoco.historico.medianaPct)}</dd></div>
          <div><dt>Dispersão (desvio-padrão)</dt><dd>{territorioEmFoco.historico.desvioPct === null ? "—" : formatarTaxa(territorioEmFoco.historico.desvioPct).replace("+", "")}</dd></div>
        </dl>
        <p className="ferramenta-apoio">{territorioEmFoco.historico.nota}</p>
      </div>}
      <div className="ferramenta-detalhe-acoes">
        <button type="button" className="analise-botao-secundario" onClick={() => setEtapa(1)}>Voltar</button>
        <button type="button" data-testid="simulador-avancar-2" className="analise-botao-primario" onClick={() => setEtapa(3)}>Seguir: intervenções e horizonte</button>
      </div>
    </div>}

    {etapa === 3 && <div data-testid="simulador-intervencoes-etapa" className="ferramenta-etapa-corpo">
      <div className="ferramenta-controles">
        <label className="analise-rotulo-campo">Data final do cenário
          <input type="month" data-testid="simulador-horizonte" className="analise-campo" value={paraCampoDeMes(config.horizonte)} min={paraCampoDeMes(anosDepois(ultimoRegistro, 0))}
            onChange={event => mudar({ horizonte: doCampoDeMes(event.target.value) })}/></label>
        <div role="group" aria-label="Atalhos da data final" className="ferramenta-atalhos">
          {[1, 2, 4, 10].map(anos => <button key={anos} type="button" data-testid={"simulador-atalho-" + anos} className="analise-botao-secundario"
            aria-pressed={config.horizonte === anosDepois(ultimoRegistro, anos)} onClick={() => mudar({ horizonte: anosDepois(ultimoRegistro, anos) })}>
            {anos === 1 ? "1 ano" : anos + " anos"} depois do último registro</button>)}
        </div>
      </div>
      <p className="ferramenta-apoio">Os atalhos são só atalhos: qualquer mês depois do último registro vale como data final. A faixa de 80% existe até 4 anos; além disso, é
        indisponível.</p>
      <p className="ferramenta-cartao-titulo">Intervenções hipotéticas</p>
      <p className="ferramenta-apoio">Acréscimos e retiradas somam-se à base do cenário; o crescimento histórico não é aplicado aos médicos acrescentados. Permanência de 100% ao
        ano (todos ficam) é a hipótese padrão. Um acréscimo anual acontece uma vez por ano.</p>
      <p data-testid="simulador-por-territorio" role="note" className="ferramenta-aviso">{total > 1
        ? <>Cada intervenção vale para <strong>cada território</strong> do cenário, não para o total: com {total.toLocaleString("pt-BR")} territórios na seleção do
          Simulador, um acréscimo de 5 médicos soma 5 a cada um deles (municípios, estados como unidade e conjuntos).</>
        : <>A intervenção vale para o território do cenário. Com mais territórios, ela vale para cada um deles, não para o total.</>}</p>
      {(config.modo === "simples" ? config.cenarios.slice(0, 1) : config.cenarios).map((cenario, indice) => intervencoesDo(cenario, indice))}
      <div className="ferramenta-detalhe-acoes">
        <button type="button" className="analise-botao-secundario" onClick={() => setEtapa(2)}>Voltar</button>
        <button type="button" data-testid="simulador-calcular" className="analise-botao-primario" disabled={!!pendencia || carregando} onClick={calcular}>
          {carregando ? "Calculando…" : "Calcular os cenários"}</button>
        {pendencia && <span data-testid="simulador-pendencia" role="status" className="ferramenta-apoio">{pendencia}</span>}
      </div>
    </div>}

    {erro && <p data-testid="simulador-erro" role="alert" className="analise-motivo">{erro}</p>}
    {etapa !== 3 && etapa !== 4 && <div className="ferramenta-detalhe-acoes analise-nao-imprimir">
      <button type="button" data-testid="simulador-calcular-direto" className="analise-botao-secundario" disabled={!!pendencia || carregando} onClick={calcular}>
        {carregando ? "Calculando…" : resposta ? "Calcular de novo" : "Calcular com o que está escolhido"}</button>
    </div>}

    {etapa === 4 && resposta && <div data-testid="simulador-resultados" className="ferramenta-etapa-corpo">
      {desatualizado && <p data-testid="simulador-desatualizado" role="status" className="ferramenta-exploratorio">As escolhas mudaram depois deste cálculo.{" "}
        <button type="button" className="analise-link" disabled={!!pendencia || carregando} onClick={calcular}>Calcular de novo</button></p>}
      <div className="ferramenta-controles">
        <label className="analise-rotulo-campo">Território no gráfico
          <select data-testid="simulador-foco" className="analise-campo" value={territorioEmFoco?.id ?? ""} onChange={event => setFoco(event.target.value)}>
            {resposta.territorios.map(item => <option key={item.id} value={item.id}>{item.rotulo}</option>)}
          </select></label>
        <button type="button" data-testid="simulador-exportar-csv" className="analise-botao-secundario"
          onClick={() => baixar("cenarios_" + resposta.horizonte.data + ".csv", csvDoSimulador(resposta), "text/csv;charset=utf-8")}>
          <Download size={14} aria-hidden="true"/>Exportar os resultados (CSV)</button>
        {resposta.referencias.length > 0 && <button type="button" data-testid="simulador-exportar-comparacoes" className="analise-botao-secundario"
          onClick={() => baixar("comparacoes_" + resposta.horizonte.data + ".csv", csvDasComparacoes(resposta), "text/csv;charset=utf-8")}>
          <Download size={14} aria-hidden="true"/>Exportar as comparações (CSV)</button>}
      </div>
      {resposta.referencias.length > 0 && <div data-testid="simulador-referencias-do-calculo" data-metrica={resposta.comparacao.metrica} className="ferramenta-apoio">
        Referências deste cálculo, comparadas por {resposta.comparacao.metrica === "taxa" ? "taxa por 1.000 habitantes (hipótese: população " +
          (resposta.comparacao.hipoteseDePopulacao ?? "constante") + ")" : "quantidade de médicos"}:{" "}
        {resposta.referencias.map(ref => ref.rotulo + " — " + (ref.estado === "calculada" ? ref.descricao ?? "" : "não calculável: " + (ref.motivo ?? "")) +
          (ref.unidade ? ". Contagem: " + ref.unidade : "")).join(". ")}.{" "}
        <button type="button" className="analise-link analise-nao-imprimir" onClick={() => setEtapa(1)}>Mudar as referências (etapa 1)</button></div>}
      {territorioEmFoco && <>
        <p className="ferramenta-apoio">Contagem: {territorioEmFoco.unidade}.{territorioEmFoco.membros.length > 0 && " Componentes: " + territorioEmFoco.membros.join(", ") + "."}</p>
        <GraficoDoCenario territorio={territorioEmFoco} ultimoRegistro={resposta.ultimoRegistro} cores={cores} metrica={resposta.comparacao.metrica}/>
        <ul data-testid="simulador-textos" className="ferramenta-fenomenos" aria-label={"Cenários de " + territorioEmFoco.rotulo}>
          {territorioEmFoco.cenarios.map(cenario => <li key={cenario.id} data-testid="simulador-cenario-resultado" data-id={cenario.id} data-estado={cenario.estado}
            data-metodo={cenario.metodo.usado ?? ""} className="ferramenta-fenomeno ferramenta-cenario-resultado">
            <p className="ferramenta-cartao-titulo"><span className="ferramenta-cor" style={{ background: cores.get(cenario.id) }} aria-hidden="true"/>{cenario.nome}
              {cenario.metodo.provisorio && cenario.estado === "calculado" && <span className="analise-marca-grupo">método provisório</span>}</p>
            {cenario.estado === "calculado" ? <>
              <p data-testid="simulador-texto" className="ferramenta-texto-do-cenario">{cenario.texto}</p>
              <p data-testid="simulador-contas" className="ferramenta-apoio">{contasDoFinal(cenario)}</p>
              <p data-testid="simulador-faixa-texto" className="ferramenta-apoio">{textoDaFaixa(cenario, territorioEmFoco.tipo === "conjunto")}</p>
              {cenario.avisos.length > 0 && <ul data-testid="simulador-avisos" className="ferramenta-notas">{cenario.avisos.map(aviso => <li key={aviso.codigo} data-codigo={aviso.codigo}>{aviso.texto}</li>)}</ul>}
              {cenario.comparacoes.length > 0 && <ul data-testid="simulador-comparacoes" className="ferramenta-notas" aria-label={"Comparação de " + cenario.nome + " com as referências"}>
                {cenario.comparacoes.map(comparacao => <li key={comparacao.id} data-testid="simulador-comparacao" data-ref={comparacao.id} data-estado={comparacao.estado}
                  data-alcance={comparacao.alcance?.estado ?? ""}>{comparacao.estado === "calculada" ? comparacao.texto
                    : "Referência " + comparacao.rotulo + ": comparação não calculável. " + (comparacao.motivo ?? "")}
                  {comparacao.avisos.map(aviso => <span key={aviso} data-testid="simulador-comparacao-aviso" className="ferramenta-apoio block">{aviso}</span>)}</li>)}
              </ul>}
              {cenario.planejamento && <div data-testid="simulador-planejamento" data-estado={cenario.planejamento.estado} data-por-evento={cenario.planejamento.porEvento ?? ""}
                data-eventos={cenario.planejamento.eventos} className="ferramenta-plano-resultado">
                <p className="ferramenta-cartao-titulo">Planejamento inverso<span className="analise-marca-grupo">conta condicional</span></p>
                {cenario.planejamento.texto ? <p data-testid="simulador-planejamento-texto" className="ferramenta-texto-do-cenario">{cenario.planejamento.texto}</p>
                  : <p data-testid="simulador-planejamento-motivo" role="status" className="analise-motivo">{cenario.planejamento.meta ? cenario.planejamento.meta.rotulo + ". " : ""}
                    {cenario.planejamento.estado === "nao_alcancavel" ? "Não alcançável: " : "Não calculável: "}{cenario.planejamento.motivo}</p>}
                {cenario.planejamento.estado === "calculado" && cenario.planejamento.intervencao && (resposta.territorios.length === 1
                  ? <button type="button" data-testid="simulador-planejamento-usar" className="analise-botao-secundario analise-nao-imprimir"
                    disabled={(config.cenarios.find(item => item.id === cenario.id)?.intervencoes.length ?? MAX_INTERVENCOES) >= MAX_INTERVENCOES}
                    title="Põe este acréscimo entre as intervenções do cenário, no lugar do planejamento inverso; depois, calcule de novo"
                    onClick={() => usarOPlano(cenario.id, cenario.planejamento!)}>Usar como intervenção deste cenário</button>
                  : <p className="ferramenta-apoio">Com mais de um território, o número é próprio de cada um. Para usá-lo como intervenção, deixe só este território no
                    Simulador.</p>)}
              </div>}
              {hipotesePertinente(cenario.hipotetico) && <div data-testid="simulador-hipotetico" data-classe={cenario.hipotetico.classe ?? ""} className="ferramenta-hipotese">
                <p className="ferramenta-cartao-titulo">Dependência de poucos médicos, no cenário<span className="analise-marca-grupo">{cenario.hipotetico.rotulo}</span></p>
                <p className="ferramenta-apoio">{textoDaHipotese(cenario.hipotetico)}</p>
              </div>}
            </> : <p data-testid="simulador-motivo" role="status" className="analise-motivo">{cenario.estado === "retirada_acima_do_estoque" ? "Retirada acima do estoque: "
              : cenario.estado === "nao_aplicavel" ? "Não se aplica: " : "Não calculável: "}{cenario.motivo}</p>}
          </li>)}
        </ul>
      </>}
      <div className="ferramenta-rolagem"><table data-testid="simulador-tabela" className="analise-tabela ferramenta-tabela">
        <caption className="ferramenta-apoio">Médicos na data final ({competenciaCurta(resposta.horizonte.data)}), por território e cenário; entre parênteses, a faixa de 80%,
          quando há (nos conjuntos, uma aproximação: a dos municípios com o porte da soma). Cada intervenção vale para cada território: cada linha recebe
          o acréscimo ou a retirada inteiros. Valores de cenário, com uma casa; a precisão integral vai no CSV.</caption>
        <thead><tr><th scope="col">Território</th><th scope="col">Último registro usável</th>
          {(resposta.territorios[0]?.cenarios ?? []).map(cenario => <th key={cenario.id} scope="col">{cenario.nome}</th>)}</tr></thead>
        <tbody>{resposta.territorios.map(item => {
          const origem = item.cenarios.find(cenario => cenario.parametros.origem);
          return <tr key={item.id} data-testid="simulador-linha" data-id={item.id}>
            <th scope="row"><button type="button" className="ferramenta-abrir" onClick={() => setFoco(item.id)}>{item.rotulo}</button></th>
            <td>{origem ? competenciaCurta(String(origem.parametros.origem)) + " · " + formatarMedicos(Number(origem.parametros.n0)) : "sem registro na janela"}</td>
            {item.cenarios.map(cenario => cenarioDaTabela(cenario, item.tipo === "conjunto"))}
          </tr>;
        })}</tbody>
      </table></div>
      <div className="ferramenta-metodo">
        <button type="button" data-testid="simulador-validacao-botao" className="analise-link" aria-expanded={verValidacao} onClick={() => setVerValidacao(valor => !valor)}>
          {verValidacao ? "Fechar “Como os métodos se saíram no passado”" : "Como os métodos se saíram no passado"}</button>
        {verValidacao && <div data-testid="simulador-validacao" className="ferramenta-metodo-corpo">
          <ul className="ferramenta-notas">{resposta.notas.map(nota => <li key={nota}>{nota}</li>)}</ul>
          <div className="ferramenta-rolagem"><table data-testid="simulador-faixas" className="analise-tabela ferramenta-tabela">
            <caption className="ferramenta-apoio">Faixas de 80% do método padrão dos municípios, medidas no passado da própria base (retroprojeção com origens em{" "}
              {resposta.retroprojecao.origens.map(competenciaCurta).join(", ")}): quanto o observado ficou acima ou abaixo do cenário, em 80% dos casos.</caption>
            <thead><tr><th scope="col">Médicos na origem</th>{[1, 2, 3, 4].map(anos => <th key={anos} scope="col">{anos === 1 ? "1 ano" : anos + " anos"}</th>)}</tr></thead>
            <tbody>{[...new Set(resposta.retroprojecao.faixas.map(faixa => faixa.porte))].map(porte => <tr key={porte}><th scope="row">{porte}</th>
              {[1, 2, 3, 4].map(anos => { const faixa = resposta.retroprojecao.faixas.find(item => item.porte === porte && item.anos === anos);
                return <td key={anos}>{faixa ? formatarPercentualInteiro(faixa.inferiorPct) + " a " + formatarPercentualInteiro(faixa.superiorPct) : "indisponível"}
                  {faixa && <span className="ferramenta-apoio block">{faixa.rotulo}; {faixa.origens} origens, {faixa.casos.toLocaleString("pt-BR")} casos</span>}</td>; })}</tr>)}</tbody>
          </table></div>
          <div className="ferramenta-rolagem"><table data-testid="simulador-erros" className="analise-tabela ferramenta-tabela">
            <caption className="ferramenta-apoio">Erro de cada método frente à persistência (M0), em 4 anos: abaixo de 1, o método errou menos que a persistência; acima, errou mais.</caption>
            <thead><tr><th scope="col">Médicos na origem</th>{["M0d", "M1", "M2", "M3"].map(metodo => <th key={metodo} scope="col">
              {NOME_CURTO_DO_METODO[metodo]} ({metodo})</th>)}</tr></thead>
            <tbody>{[...new Set(resposta.retroprojecao.tabela.map(linha => linha.porte))].map(porte => <tr key={porte}><th scope="row">{porte}</th>
              {["M0d", "M1", "M2", "M3"].map(metodo => { const linha = resposta.retroprojecao.tabela.find(item => item.porte === porte && item.metodo === metodo && item.anos === 4);
                return <td key={metodo}>{linha?.frenteAoM0 === null || linha?.frenteAoM0 === undefined ? "—" : linha.frenteAoM0.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>; })}</tr>)}</tbody>
          </table></div>
        </div>}
      </div>
      <p data-testid="simulador-versoes" className="ferramenta-apoio">Método {resposta.versao} · base {resposta.fonte.base} ({resposta.fonte.categoria.toLowerCase()}), versão{" "}
        {resposta.fonte.versao.slice(0, 12)} · janela de {competenciaCurta(resposta.janela.inicio)} a {competenciaCurta(resposta.janela.fim)}{resposta.janela.padrao ? " (padrão)" : ""} ·
        origem de cada cenário: o último registro usável do território na janela · último registro da base: {competenciaCurta(resposta.ultimoRegistro)}.</p>
    </div>}
    {carregando && !resposta && <p role="status" className="analise-vazio"><LoaderCircle size={18} className="animate-spin" aria-hidden="true"/>Calculando os cenários…</p>}
  </section>;
}
