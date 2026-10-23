import type { ReactNode } from "react";
import type { PainelIndicador, PainelItem } from "./painelApi";
import type { Dica, Escala, Pintura, RotulosTerritoriais } from "./painelModel";

// Contrato entre a área de análise (AreaDeAnalise.tsx), o mapa (MapaAnalise.tsx), a transição entre as vistas
// (transicaoVistas.ts), o mapinha (MiniMapa.tsx), o gráfico (PainelChart.tsx) e o motor (POST /api/painel/mapa). Só tipos: a
// lógica fica em cada módulo. O mapa só desenha o que o motor devolveu; nada é calculado na tela (RQ-REP-09). Trocar de vista
// é estado visual e não inicia análise (RQ-REP-06).

/** Vista do desenho: o gráfico de bolhas, o mapa ou os dois lado a lado (só em telas largas). */
export type VistaDesenho = "grafico" | "mapa" | "lado";

/** Resposta de POST /api/painel/mapa, normalizada pelo cliente (painelApi.pedirMapa). */
export type DadosDoMapa = {
  competencia: string;
  /** "SIRGAS2000" ou "WGS84": o referencial das coordenadas. Só para o desenho; o mapa não mede distância. */
  referencial: string;
  /** Coordenadas autorizadas de todas as unidades da fonte na competência (na base do Brasil, a sede municipal do IBGE):
   * id → [latitude, longitude], em graus decimais. As unidades fora da análise servem de fundo (cinza claro). */
  pontos: Map<string, [number, number]>;
  /** Unidades sem coordenada válida, com o motivo do motor: ficam fora do mapa e entram em "Não avaliáveis". */
  semCoordenada: { id: string; rotulo: string; motivo: string }[];
};

/**
 * Como o mapa pinta os pontos:
 * - "camada": a mesma pintura do gráfico (grupos, faixas, condições, ordem, classes ou variação), pela função `pintar`;
 * - "continua": mapeamento visual contínuo de `valorContinuo` no `dominio` (linear por padrão; logarítmica só por escolha da
 *   pessoa), transformação admitida pela Parte 13 da SPEC; a legenda diz que a cor não é classe nem limiar;
 * - "pergunta": a análise ainda não tem cor escolhida: pontos neutros e a pergunta "Como pintar o mapa?" (decisão de 23/10).
 */
export type PinturaDoMapa = "camada" | "continua" | "pergunta";

/** Opções da pergunta "Como pintar o mapa?". Quintis e faixas vêm do motor (CAP-DIS-02 e CAP-DIS-03), só na distribuição;
 * "condicoes" abre o painel Condições. */
export type EscolhaDePintura = "quintis" | "faixas" | "continua" | "condicoes";

/** Codificação do tamanho (área proporcional): população na densidade, quantidade na quantidade, coorte inicial na rotatividade. */
export type TamanhoDoMapa = { valor: (item: PainelItem) => number | null; rotulo: string; maximo: number | null };

export type MapaProps = {
  /** Itens desenháveis (os mesmos do gráfico). Conjuntos não têm ponto: os membros ganham contorno. Estados não chegam ao mapa. */
  itens: PainelItem[];
  /** Ids dentro da régua e dos filtros visuais; os demais itens ficam esmaecidos, e não escondidos (decisão de 23/10). */
  dentro: Set<string>;
  dados: DadosDoMapa;
  indicador: PainelIndicador;
  pintura: PinturaDoMapa;
  /** A mesma função de pintura do gráfico (pintura = "camada"). */
  pintar: (item: PainelItem) => Pintura;
  /** Valor da cor contínua (pintura = "continua"): o indicador, ou a permanência da coorte na rotatividade. */
  valorContinuo: (item: PainelItem) => number | null;
  /** Rótulo da cor contínua na legenda, com a unidade (por exemplo "Densidade (por 1.000 habitantes)"). */
  rotuloContinuo: string;
  /** Domínio do valor contínuo, do motor (resposta.dominios) ou fixo (0 a 100 na permanência). */
  dominio: [number, number] | null;
  /** Escala da cor contínua: linear (padrão) ou logarítmica (só por escolha). */
  escala: Escala;
  tamanho: TamanhoDoMapa;
  /** Valor do Brasil: só uma marca de contexto na legenda contínua; nunca classifica ponto nenhum. */
  contextoBrasil: { valor: number; rotulo: string } | null;
  /** Legenda da camada em uso (a mesma do gráfico), mostrada com pintura = "camada". */
  legendaCor: ReactNode;
  /** Opções da pergunta nesta análise. */
  opcoesDePintura: EscolhaDePintura[];
  onEscolherPintura: (escolha: EscolhaDePintura) => void;
  selecionados: string[];
  /** Membros da referência (a mesma mira do gráfico). */
  referencias: string[];
  /** Ligações ilustrativas até a referência mais próxima, só dos selecionados (até 30), com o aviso "ligação ilustrativa, não é
   * trajeto". */
  ligacoes: { de: string; para: string[] }[];
  /** Texto antes do nome (por exemplo "1º" na ordenação, posição do motor). */
  extraDoRotulo?: (item: PainelItem) => string | null;
  /** A mesma dica do gráfico (montarDica). */
  dicaDe: (item: PainelItem) => Dica;
  rotulos: RotulosTerritoriais;
  /** Destaque cruzado com o gráfico (lado a lado): o item sob o mouse no gráfico, e o aviso do item sob o mouse no mapa. */
  ativoExterno?: string | null;
  onAtivo?: (id: string | null) => void;
  /** Clique ou Enter: marca e desmarca, como na bolha. */
  onAlternar: (id: string) => void;
  carregando: boolean;
};

/** Posição de uma bolha ou ponto na janela (px, coordenadas de getBoundingClientRect), para a transição entre as vistas. */
export type PosicaoNaTela = { x: number; y: number; r: number; cor: string };
export type Posicoes = Map<string, PosicaoNaTela>;

/** Alça do mapa (ref de MapaAnalise). */
export type MapaHandle = { posicoes: () => Posicoes; verTudo: () => void };

/** transicaoVistas.ts: posições das bolhas do gráfico na janela, a partir do elemento que contém o gráfico. */
export type PosicoesDoGrafico = (raiz: HTMLElement) => Posicoes;
/** transicaoVistas.ts: anima, numa camada por cima de `raiz`, cada id de `origem` até a mesma id em `destino` (os que só
 * existem num lado aparecem ou somem); resolve ao terminar e remove a camada. */
export type AnimarTransicao = (raiz: HTMLElement, origem: Posicoes, destino: Posicoes, duracaoMs: number) => Promise<void>;

/** MiniMapa.tsx: o Brasil (ou a planilha) em pontos cinza e um destaque; na dica do gráfico e no canto do mapa com zoom. */
export type MiniMapaProps = {
  pontos: Map<string, [number, number]>;
  destaque: string | null;
  /** Retângulo da área à vista (em graus), no canto do mapa com zoom. */
  enquadramento?: { latMin: number; latMax: number; lonMin: number; lonMax: number } | null;
  tamanho?: number;
};

/** Props novas do gráfico (PainelChart.tsx): o mapinha na dica e o destaque cruzado com o mapa (lado a lado). */
export type GraficoComMapaProps = {
  pontosDoMapa?: Map<string, [number, number]> | null;
  ativoExterno?: string | null;
  onAtivo?: (id: string | null) => void;
};

/**
 * Seletores estáveis (roteiros de navegador). Não colidem com "analise-vista-inicial/final" (Primeira | Última da Tendência).
 * - Área: `area-de-analise` com `data-desenho` = grafico | mapa | lado.
 * - Escolha da vista: grupo `analise-desenho`; botões `analise-desenho-grafico`, `analise-desenho-mapa` e `analise-desenho-lado`
 *   (este só em telas largas), com aria-pressed; motivo de vista indisponível `analise-desenho-motivo`; atalho
 *   `analise-desenho-atalho` ("Ver os municípios no mapa").
 * - Ajustes da análise, dentro da aba escolhida: `analise-ajustes` com `data-familia`.
 * - Convite: `analise-convite-mapa` ("Ver onde ficam no mapa").
 * - Frase-resumo do motor: `analise-resumo`.
 * - Mapa: `mapa-analise` com `data-pintura`, `data-pontos` (pontos do resultado desenhados), `data-contexto` (pontos de fundo),
 *   `data-esmaecidos` e `data-escala`; dica `mapa-dica`; pergunta `mapa-pergunta` e botões `mapa-pergunta-<escolha>`; legenda
 *   `mapa-legenda` com `data-tipo` = camada | continua | pergunta; legenda de tamanho `mapa-legenda-tamanho`; controles
 *   `mapa-ampliar`, `mapa-reduzir` e `mapa-ver-tudo`; nota do ponto `mapa-nota`; aviso das ligações `mapa-ligacoes`.
 * - Mapinha: `minimapa` (na dica do gráfico, `analise-dica`, e no canto do mapa com zoom).
 * - Gancho de teste (como o __adtMapModel do mapa antigo): `window.__adtMapa` = { pintura, escala, dominio, contexto,
 *   pontos: [{ id, x, y, r, cor, esmaecido, selecionado }] }, atualizado a cada desenho.
 */

