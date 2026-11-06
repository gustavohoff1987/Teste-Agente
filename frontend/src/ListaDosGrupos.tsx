import type { PainelItem } from "./painelApi";
import type { LinhaDeReferencia } from "./PainelChart";
import { INDICADORES, formatarNumero } from "./painelModel";

// A lista ordenada dos grupos em tela estreita (06/11/2026, item 7 do comando de navegação por níveis): vendo por estado, no
// celular, o padrão é uma linha por estado, na ordem do motor (`ordem_do_indicador`, CAP-SUB-02, sem mostrar as posições), com a
// sigla (ou o nome, quando a base não tem sigla), um ponto na escala do indicador (a partir do zero), o valor e a marca do todo.
// Tocar numa linha desce até o estado. A tela não ordena nem calcula: a ordem e os valores vêm do motor; a escala só posiciona.

export type ListaDosGruposProps = {
  itens: PainelItem[];
  ordem: { id: string; posicao: number | null }[];
  indicador: "densidade" | "quantidade";
  /** A linha do todo ("Brasil 2,36"), do motor. */
  todo: LinhaDeReferencia | null;
  limiares: number[];
  /** O nome dos grupos da base no plural ("estados"), para o nome da lista. */
  plural: string;
  onAbrir: (id: string) => void;
};

const siglaDe = (item: PainelItem) => item.uf || (/\(([^()]+)\)\s*$/.exec(item.rotulo) || [])[1] || item.rotulo;

export default function ListaDosGrupos(p: ListaDosGruposProps) {
  const porId = new Map(p.itens.map(item => [item.id, item]));
  const linhas = p.ordem.map(entrada => porId.get(entrada.id)).filter((item): item is PainelItem => !!item);
  const valorDe = (item: PainelItem) => p.indicador === "densidade" ? item.densidade : item.quantidade;
  const valores = linhas.map(valorDe).filter((valor): valor is number => valor !== null && Number.isFinite(valor));
  const maximo = Math.max(0, p.todo?.valor ?? 0, ...valores);
  const posicao = (valor: number) => (maximo > 0 ? Math.max(0, Math.min(100, valor / maximo * 100)) : 0) + "%";
  const especie = INDICADORES[p.indicador];
  return <div data-testid="analise-lista-grupos" className="analise-lista-grupos">
    {p.todo && <p data-testid="analise-lista-todo" className="analise-lista-cabecalho">
      <span className="analise-lista-todo-amostra" aria-hidden="true"/>{p.todo.rotulo}</p>}
    <ol aria-label={"Os " + p.plural + " do maior para o menor valor"} className="analise-lista-linhas">
      {linhas.map(item => {
        const valor = valorDe(item);
        const texto = valor === null ? "sem valor" : formatarNumero(valor, especie.contagem, p.limiares);
        return <li key={item.id}>
          <button type="button" data-testid="analise-lista-grupo" data-id={item.id} data-valor={valor ?? ""}
            className="analise-lista-linha" onClick={() => p.onAbrir(item.id)}
            aria-label={item.rotulo + ": " + texto + (valor === null ? "" : " " + especie.unidade) + ". Toque para abrir."}>
            <span className="analise-lista-sigla" title={item.rotulo}>{siglaDe(item)}</span>
            <span className="analise-lista-trilho" aria-hidden="true">
              {p.todo && <span className="analise-lista-todo-marca" style={{ left: posicao(p.todo.valor) }}/>}
              {valor !== null && <span className="analise-lista-ponto" style={{ left: posicao(valor) }}/>}
            </span>
            <span className="analise-lista-valor">{texto}</span>
          </button>
        </li>;
      })}
    </ol>
  </div>;
}
