import { useEffect, useMemo, useState, type RefObject } from "react";
import MapaDosConjuntos, { type PinturaDoPonto } from "./MapaDosConjuntos";
import { carregarMalha, divisasDoMapa, type Malha } from "./malhaModel";
import PainelChart, { tamanhoDoGrafico, useLargura } from "./PainelChart";
import PainelSeries from "./PainelSeries";
import type { PainelResposta, RotulosTerritoriais } from "./painelApi";
import { ROTULOS_BRASIL, paletaDoGrafico } from "./painelModel";
import { useEsquemaDeCor } from "./useEsquemaDeCor";
import {
  CORES_DOS_NIVEIS, NIVEIS, NOMES_DOS_NIVEIS, artigoDaUnidade, camadasDoMapa, competenciaCurta, criterioDoContexto, dicaDoSinal, dominiosDoContexto, formatarInteiro,
  foraDoMapa, formatarTaxa, itensDoContexto, maisProximo, nivelNoDesenho, nomeDoSinal, seriesDoComparativo, textoDasCoordenadasOficiais,
  textoDeForaDoMapa, textoDosTrechos,
  type DetalheDoDetector, type LinhaDoDetector, type NivelDoAlerta, type RespostaDoDetector,
} from "./detectorModel";

// As visões Mapa e Gráfico do Detector de Sinais (comando V23, Proposta V3, seção B.3) e a série da taxa do detalhe, com os
// componentes que o Agente já tem. Nada é calculado aqui: o mapa, as bolhas e a série desenham os valores, os níveis e as
// coordenadas que o motor mandou (POST /api/detector).
// - MapaDosNiveis: o mapa de pontos da Seleção (MapaDosConjuntos), com cada município pintado pelo nível do alerta (ou, com o
//   filtro "Sinal", pelo nível daquele sinal), os conjuntos pelo contorno e o nome de cada grupo de cima junto aos pontos dele.
//   Na base do Brasil (etapa 7 do comando V23), o mapa tem as divisas da malha municipal do IBGE, pedida só quando ele abre: as
//   dos estados ficam sempre à vista; as dos municípios aparecem quando o mapa é aproximado num estado ou quando os territórios
//   à vista são de um estado só; a área de cada município com nível leva a cor dele. Numa planilha, não há malha: o mapa segue
//   sem divisas e diz isso (o nome do grupo situa os pontos).
// - BolhasDoContexto: o gráfico de bolhas do Agente (PainelChart), com X = a distância até o território mais próximo que atende
//   ao critério (sinal 11), Y = a taxa por 1.000 habitantes (sinal 8), o tamanho pela população e a cor pelo nível.
// - SerieDaTaxa: a Série temporal do Agente (PainelSeries), com a taxa do território e a da referência dele (sinais 8 e 10).
// O nível vem sempre escrito também (legenda, dica e lista), nunca só pela cor; desde o AJ-04 (18/11/2026), a dica de um território
// nomeia o sinal pintado — o principal do alerta ou, com o filtro "Sinal", aquele sinal —, com o nível, e diz quantos outros sinais
// com nível ele tem ("Poucos médicos · elevado; mais 1 sinal com nível"). Os nomes ("município", "estado") são os da base
// (`fonte.rotulos`); numa planilha enviada, o gráfico e a série usam os nomes do painel "Colunas" (`rotulosDoPainel`).

type DoDetector = { resposta: RespostaDoDetector; linhas: LinhaDoDetector[]; sinal: string };
const RAIOS: Record<NivelDoAlerta, number> = { moderado: 3.2, elevado: 4, critico: 4.8 };

/** A legenda dos níveis: a cor, o nome por extenso e quantos territórios à vista. */
function LegendaDosNiveis({ contagens, semNivel }: { contagens: Record<NivelDoAlerta, number>; semNivel: number }) {
  return <p data-testid="detector-legenda-niveis" className="ferramenta-legenda">
    {NIVEIS.map(nivel => <span key={nivel} data-nivel={nivel} data-quantos={contagens[nivel]}>
      <span className="ferramenta-nivel-ponto" style={{ background: CORES_DOS_NIVEIS[nivel] }} aria-hidden="true"/>
      {NOMES_DOS_NIVEIS[nivel]}: {formatarInteiro(contagens[nivel])}</span>)}
    <span data-nivel="" data-quantos={semNivel}><span className="ferramenta-nivel-ponto ferramenta-nivel-ponto-sem" aria-hidden="true"/>
      Sem nível no desenho: {formatarInteiro(semNivel)}</span>
  </p>;
}

export function MapaDosNiveis({ resposta, linhas, sinal, onAbrir }: DoDetector & { onAbrir: (id: string) => void }) {
  const r = resposta.fonte.rotulos;
  const camadas = useMemo(() => camadasDoMapa(resposta, linhas, sinal), [resposta, linhas, sinal]);
  const coordenadas = useMemo(() => new Map(Object.entries(resposta.coordenadas)), [resposta.coordenadas]);
  const nomes = useMemo(() => new Map(resposta.linhas.map(linha => [linha.id, linha.rotulo])), [resposta.linhas]);
  const naLista = useMemo(() => new Set(resposta.linhas.map(linha => linha.id)), [resposta.linhas]);
  const pintura = useMemo(() => {
    const porId = new Map(linhas.map(linha => [linha.id, linha]));
    const mapa = new Map<string, PinturaDoPonto>();
    for (const nivel of NIVEIS) for (const id of camadas.porNivel[nivel]) {
      const daLinha = porId.get(id);
      mapa.set(id, { cor: CORES_DOS_NIVEIS[nivel], raio: RAIOS[nivel], chave: nivel,
        rotulo: (daLinha && dicaDoSinal(daLinha, sinal, r)) || "nível " + NOMES_DOS_NIVEIS[nivel].toLowerCase() });
    }
    return mapa;
  }, [camadas, linhas, sinal, r]);
  const contagens = { critico: camadas.porNivel.critico.length, elevado: camadas.porNivel.elevado.length, moderado: camadas.porNivel.moderado.length };
  const fora = useMemo(() => foraDoMapa(resposta, linhas, sinal), [resposta, linhas, sinal]);
  const textoDeFora = textoDeForaDoMapa(fora, r, resposta.janela.fim);
  const textoDasOficiais = useMemo(() => textoDasCoordenadasOficiais(resposta, linhas, r), [resposta, linhas, r]);
  const doQue = sinal === "todos" || sinal === "juntos" || sinal === "registro" ? "do alerta do território" : "de “" + nomeDoSinal(sinal, r) + "”";
  const doBrasil = resposta.fonte.origem === "brasil", comGrupo = resposta.fonte.tem.grupo, oGrupo = r.oGrupo ?? "o " + r.grupo;
  // As divisas (etapa 7 do comando V23): só a base do Brasil tem a malha (a municipal do IBGE, um arquivo versionado da interface),
  // e ela só é pedida quando o mapa abre. `undefined`: ainda carregando; `null`: sem malha (uma planilha, ou o arquivo não pôde ser
  // lido) — o mapa segue só com os pontos e diz isso.
  const [malha, setMalha] = useState<Malha | null | undefined>(doBrasil ? undefined : null);
  useEffect(() => {
    if (!doBrasil) { setMalha(null); return; }
    let vivo = true;
    setMalha(undefined);
    carregarMalha(import.meta.env.BASE_URL || "/").then(lida => { if (vivo) setMalha(lida); });
    return () => { vivo = false; };
  }, [doBrasil]);
  // "Aproximar o mapa em": um dos estados dos territórios à vista. O estado escolhido sai quando deixa de estar à vista.
  const [aproximado, setAproximado] = useState("");
  const estados = useMemo(() => camadas.grupos.map(grupo => ({ prefixo: (grupo.membros[0] ?? "").replace(/^code:/, "").slice(0, 2), sigla: grupo.nome }))
    .filter(estado => estado.prefixo).sort((a, b) => a.sigla.localeCompare(b.sigla, "pt-BR")), [camadas]);
  const emFoco = estados.some(estado => estado.prefixo === aproximado) ? aproximado : "";
  const divisas = useMemo(() => !malha ? undefined : divisasDoMapa(malha, linhas.filter(linha => linha.tipo === "municipio").map(linha => {
    const nivel = nivelNoDesenho(linha, sinal);
    return { id: linha.id, codigo: linha.id.replace(/^code:/, ""), ...(nivel ? { cor: CORES_DOS_NIVEIS[nivel], chave: nivel } : {}) };
  }), emFoco), [malha, linhas, sinal, emFoco]);
  // O desenho é feito na largura que o mapa tem na tela (o texto mantém 12 px também no celular, onde o mapa fica mais alto).
  const [refDoMapa, medida] = useLargura(760);
  const { largura, altura } = tamanhoDoGrafico(medida, 760, 440, 380);
  const estadoDasDivisas = !doBrasil ? "sem" : malha === undefined ? "carregando" : malha ? "carregadas" : "indisponiveis";
  return <figure ref={refDoMapa as RefObject<HTMLElement>} data-testid="detector-mapa" data-sinal={sinal} data-critico={contagens.critico}
    data-elevado={contagens.elevado} data-moderado={contagens.moderado} data-fundo={camadas.fundo.length} data-conjuntos={camadas.conjuntos.length}
    data-grupos={camadas.grupos.length} data-divisas={estadoDasDivisas} data-aproximado={emFoco} data-largura={largura} className="ferramenta-grafico">
    {malha && estados.length > 1 && <label className="analise-rotulo-campo ferramenta-busca analise-nao-imprimir">Aproximar o mapa em
      <select data-testid="detector-mapa-aproximar" className="analise-campo" value={emFoco} onChange={event => setAproximado(event.target.value)}>
        <option value="">todos os territórios à vista</option>
        {estados.map(estado => <option key={estado.prefixo} value={estado.prefixo}>{estado.sigla}</option>)}
      </select></label>}
    <MapaDosConjuntos coordenadas={coordenadas} fundo={camadas.fundo} conjuntos={camadas.conjuntos} pintura={pintura} grupos={camadas.grupos}
      nomeDe={id => nomes.get(id) ?? id} largura={largura} altura={altura} divisas={divisas}
      rotulo={"Mapa dos territórios à vista em " + competenciaCurta(resposta.janela.fim) + ", pelo nível " + doQue + ": " +
        formatarInteiro(contagens.critico) + " em crítico, " + formatarInteiro(contagens.elevado) + " em elevado e " + formatarInteiro(contagens.moderado) + " em moderado"}
      vazio={(artigoDaUnidade(r) === "a" ? "Nenhuma " : "Nenhum ") + r.unidade + " à vista tem coordenada válida para o mapa."}
      onTocar={id => { if (naLista.has(id)) onAbrir(id); }}
      legenda={"pontos coloridos: o nível " + doQue + " · pontos claros: sem nível · tracejado: conjunto" + (comGrupo ? " · letras: " + oGrupo + " dos pontos" : "") +
        (divisas ? " · áreas coloridas: o nível do " + r.unidade + " · linhas: as divisas" : "")}/>
    <LegendaDosNiveis contagens={contagens} semNivel={camadas.fundo.length}/>
    {/* Quem está na lista e não tem ponto: quantos, com que nível, quais e por quê (o motor diz o motivo). */}
    {textoDeFora && <p data-testid="detector-mapa-fora" data-quantos={fora.length} className="ferramenta-apoio">{textoDeFora}</p>}
    {/* Quem está no mapa com a coordenada da camada oficial do IBGE (a base traz a dele fora do intervalo válido). */}
    {textoDasOficiais && <p data-testid="detector-mapa-coordenadas-oficiais" className="ferramenta-apoio">{textoDasOficiais}</p>}
    <figcaption className="ferramenta-apoio">Onde ficam os territórios à vista, pelo nível {doQue}. Os pontos usam as coordenadas da data avaliada;{" "}
      {comGrupo ? oGrupo + " como unidade não tem ponto, e o conjunto" : "o conjunto"} aparece pelo contorno, sem nível.{" "}
      <span data-testid="detector-mapa-divisas">{estadoDasDivisas === "carregadas"
        ? "As divisas são as da malha municipal do IBGE: as dos estados ficam sempre à vista; as dos municípios aparecem quando o mapa é aproximado " +
          "num estado ou quando os territórios à vista são de um estado só. A área de cada município à vista com nível leva a cor dele" +
          (divisas?.comBordas ? "; as divisas dos municípios estão à vista" : "") + "."
        : estadoDasDivisas === "carregando" ? "As divisas estão sendo carregadas."
        : estadoDasDivisas === "indisponiveis" ? "As divisas não puderam ser carregadas: o mapa mostra só os pontos, e a sigla situa os pontos de cada " + r.grupo + "."
        : "A base não tem as divisas" + (comGrupo ? ": o nome situa os pontos de cada " + r.grupo : "") + "."}</span>{" "}
      Para ver um sinal só, escolha-o no filtro “Sinal”. Toque num ponto para abrir os detalhes do território.</figcaption>
  </figure>;
}

export function BolhasDoContexto({ resposta, linhas, sinal, onAbrir, rotulosDoPainel = ROTULOS_BRASIL }: DoDetector & { onAbrir: (id: string) => void;
  rotulosDoPainel?: RotulosTerritoriais }) {
  const paleta = paletaDoGrafico(useEsquemaDeCor());
  const r = resposta.fonte.rotulos;
  const itens = useMemo(() => itensDoContexto(linhas), [linhas]);
  const dados = useMemo(() => ({ competencia: resposta.janela.fim, competencia_inicial: null,
    dominios: dominiosDoContexto(itens) }) as unknown as PainelResposta, [resposta.janela.fim, itens]);
  const nomes = useMemo(() => new Map(itens.map(item => [item.id, item.rotulo])), [itens]);
  const niveis = useMemo(() => new Map(linhas.map(linha => [linha.id, nivelNoDesenho(linha, sinal)])), [linhas, sinal]);
  const dicas = useMemo(() => new Map(linhas.map(linha => [linha.id, dicaDoSinal(linha, sinal, r)])), [linhas, sinal, r]);
  const criterio = resposta.comparacao.contexto;
  if (!itens.length) return <p data-testid="detector-bolhas-vazio" role="status" className="ferramenta-apoio">Nenhum território à vista tem distância a
    mostrar: os que atendem ao critério não têm distância{resposta.fonte.tem.grupo ? ", e " + (r.oGrupo ?? "o " + r.grupo) + " como unidade não tem um ponto único" : ""}.</p>;
  const contagens = { critico: 0, elevado: 0, moderado: 0 };
  let semNivel = 0;
  for (const item of itens) { const nivel = niveis.get(item.id); if (nivel) contagens[nivel] += 1; else semNivel += 1; }
  return <figure data-testid="detector-bolhas" data-itens={itens.length} data-critico={contagens.critico} data-elevado={contagens.elevado}
    data-moderado={contagens.moderado} className="ferramenta-grafico">
    <PainelChart resposta={dados} itens={itens} todos={itens} indicador="densidade" escala="linear" distancia cometa={false} porItem vista="final"
      fase="parado" pintura={item => { const nivel = niveis.get(item.id); return { cor: nivel ? CORES_DOS_NIVEIS[nivel] : paleta.neutra, vazada: false, apagada: !nivel }; }}
      selecionados={[]} limiares={[]} nomes={nomes}
      carregando={false} rotuloDistancia={"Distância até " + artigoDaUnidade(r) + " " + maisProximo(r) + " que atende ao critério (km)"} rotulos={rotulosDoPainel}
      contextoBrasil={criterio.taxaMinima !== null ? { valor: criterio.taxaMinima, rotulo: "Critério " + formatarTaxa(criterio.taxaMinima) } : null}
      cortes={[]} corte={null} faixasDistancia={[]} unidadesDoGrupo={() => null} legendaCor={null} notas={[]} onAlternar={() => undefined}
      onAbrirGrupo={() => undefined} onAbrirUnidade={onAbrir} notasDaDica={item => { const dica = dicas.get(item.id); return dica ? [dica] : []; }}/>
    <LegendaDosNiveis contagens={contagens} semNivel={semNivel}/>
    <figcaption className="ferramenta-apoio">Cada bolha é um território à vista com distância a mostrar ({formatarInteiro(itens.length)}), pintado pelo
      nível. Na horizontal, a distância em linha reta até {artigoDaUnidade(r)} {criterioDoContexto(criterio.taxaMinima, r) ?? maisProximo(r) + " que atende ao critério"};
      na vertical, a taxa de {r.profissionais} por 1.000 habitantes em {competenciaCurta(resposta.janela.fim)}; o tamanho mostra a população. A linha
      tracejada é a taxa do critério. A distância é só contexto: não é distância por estrada nem acesso, e nunca vira alerta. Toque numa bolha para abrir os
      detalhes do território.</figcaption>
  </figure>;
}

export function SerieDaTaxa({ detalhe, profissionais = "médicos", rotulosDoPainel = ROTULOS_BRASIL, feminino = false }: { detalhe: DetalheDoDetector;
  profissionais?: string; rotulosDoPainel?: RotulosTerritoriais;
  /** A unidade da base é feminina ("a comuna"): a referência é "a das demais comunas". */
  feminino?: boolean }) {
  const series = useMemo(() => seriesDoComparativo(detalhe), [detalhe]);
  if (!series || !detalhe.comparativo) return null;
  return <figure data-testid="detector-serie-da-taxa" data-referencias={series.referencias.length} className="ferramenta-grafico">
    <PainelSeries itens={[series.item]} competencias={detalhe.comparativo.competencias} indicador="densidade" rotulos={rotulosDoPainel}
      referencias={series.referencias} rotuloDaData={competenciaCurta}/>
    <figcaption className="ferramenta-apoio">Taxa de {profissionais} por 1.000 habitantes de {detalhe.rotulo} em cada registro{series.referencias.length
      ? " e, tracejada, a " + (feminino && detalhe.tipo !== "estado" ? "das " : "dos ") + detalhe.comparativo.referencia.rotulo : ""}. O valor de cada data vale nela; a variação entre datas só é
      lida {textoDosTrechos(detalhe.comparativo.trechos)}, quando a população da base é comparável de um ano para o outro.
      {detalhe.comparativo.referencia.motivo ? " " + detalhe.comparativo.referencia.motivo : ""}</figcaption>
  </figure>;
}
