import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { CircleHelp } from "lucide-react";

// "Entenda" (Proposta V3, seção A.4; comando V23), igual no Detector de Sinais e no Simulador de Cenários. Fica escondido e abre
// com o mouse (ao passar por cima), com um toque ou pelo teclado (ao receber o foco; Enter ou Espaço fixam a caixa); fecha ao
// sair: o mouse deixa o botão e a caixa, o foco sai deles, Esc ou um toque fora. Traz duas ou três frases simples e um exemplo com
// números; a explicação inteira fica em "Ver explicação completa". A caixa é desenhada por cima da página, na posição do botão
// (a rolagem das tabelas não a corta), e cabe na largura do celular. Os textos vêm de quem usa o componente (do motor).

type Props = {
  /** Do que trata ("Queda recente"): o título da caixa e o nome do botão para o leitor de tela ("Entenda: Queda recente"). */
  sobre: string;
  texto: string;
  exemplo?: string | null;
  /** "Ver explicação completa": abre a explicação inteira, que fica fora da caixa. */
  onCompleta?: () => void;
  /** O prefixo dos data-testid: `<testid>`, `<testid>-botao`, `<testid>-caixa` e `<testid>-completa`. */
  testid?: string;
};
type Lugar = { left: number; width: number; top?: number; bottom?: number };

const LARGURA = 360, MARGEM = 12, FOLGA = 6, ESPERA_AO_SAIR = 160;

export default function Entenda({ sobre, texto, exemplo, onCompleta, testid = "entenda" }: Props) {
  const [aberto, setAberto] = useState(false);
  /** Fixado por um clique, um toque, Enter ou Espaço: continua aberto quando o mouse sai, até um toque fora, Esc ou a saída do foco. */
  const [fixo, setFixo] = useState(false);
  const [lugar, setLugar] = useState<Lugar | null>(null);
  const bloco = useRef<HTMLSpanElement>(null), botao = useRef<HTMLButtonElement>(null), caixa = useRef<HTMLSpanElement>(null);
  const espera = useRef<number | null>(null), semAbrirNoFoco = useRef(false);
  const id = useId();

  const cancelarEspera = () => { if (espera.current !== null) { window.clearTimeout(espera.current); espera.current = null; } };
  const abrir = () => { cancelarEspera(); setAberto(true); };
  const fechar = () => { cancelarEspera(); setAberto(false); setFixo(false); };

  // A posição da caixa: abaixo do botão (ou acima, quando não cabe), sem sair da tela; refeita na rolagem e na mudança de tamanho.
  useLayoutEffect(() => {
    if (!aberto) { setLugar(null); return; }
    const posicionar = () => {
      if (!botao.current) return;
      const r = botao.current.getBoundingClientRect();
      const width = Math.min(LARGURA, window.innerWidth - 2 * MARGEM);
      const left = Math.max(MARGEM, Math.min(r.left, window.innerWidth - width - MARGEM));
      const altura = caixa.current?.offsetHeight ?? 200;
      const cabeAbaixo = window.innerHeight - r.bottom >= altura + FOLGA + MARGEM;
      setLugar(cabeAbaixo || r.top < window.innerHeight - r.bottom ? { left, width, top: r.bottom + FOLGA }
        : { left, width, bottom: window.innerHeight - r.top + FOLGA });
    };
    posicionar();
    window.addEventListener("scroll", posicionar, true);
    window.addEventListener("resize", posicionar);
    return () => { window.removeEventListener("scroll", posicionar, true); window.removeEventListener("resize", posicionar); };
  }, [aberto]);

  // Fecha com Esc e com um toque (ou clique) fora do botão e da caixa.
  useEffect(() => {
    if (!aberto) return;
    const fora = (evento: PointerEvent) => { if (!bloco.current?.contains(evento.target as Node)) fechar(); };
    const tecla = (evento: KeyboardEvent) => {
      if (evento.key !== "Escape") return;
      evento.stopPropagation();
      const tinhaOFoco = bloco.current?.contains(document.activeElement);
      fechar();
      if (tinhaOFoco && document.activeElement !== botao.current) { semAbrirNoFoco.current = true; botao.current?.focus(); }
    };
    document.addEventListener("pointerdown", fora);
    document.addEventListener("keydown", tecla, true);
    return () => { document.removeEventListener("pointerdown", fora); document.removeEventListener("keydown", tecla, true); };
  }, [aberto]);
  useEffect(() => cancelarEspera, []);

  return <span ref={bloco} data-testid={testid} data-aberto={aberto ? "true" : "false"} className="entenda"
    onMouseEnter={abrir}
    onMouseLeave={() => { if (fixo) return; cancelarEspera(); espera.current = window.setTimeout(() => setAberto(false), ESPERA_AO_SAIR); }}
    onFocus={() => { if (semAbrirNoFoco.current) { semAbrirNoFoco.current = false; return; } abrir(); }}
    onBlur={evento => { if (!bloco.current?.contains(evento.relatedTarget as Node | null)) fechar(); }}>
    <button ref={botao} type="button" data-testid={testid + "-botao"} className="entenda-botao" aria-expanded={aberto} aria-controls={id}
      aria-label={"Entenda: " + sobre}
      onClick={() => { if (aberto && fixo) fechar(); else { setFixo(true); abrir(); } }}>
      <CircleHelp size={14} aria-hidden="true"/>Entenda</button>
    {aberto && <span ref={caixa} id={id} role="note" data-testid={testid + "-caixa"} className="entenda-caixa"
      style={lugar ? { left: lugar.left, width: lugar.width, top: lugar.top, bottom: lugar.bottom } : { visibility: "hidden", left: 0, top: 0 }}>
      <strong className="entenda-titulo">{sobre}</strong>
      <span className="entenda-texto">{texto}</span>
      {exemplo && <span data-testid={testid + "-exemplo"} className="entenda-exemplo"><strong>Exemplo:</strong> {exemplo}</span>}
      {onCompleta && <button type="button" data-testid={testid + "-completa"} className="analise-link entenda-completa"
        onClick={() => { fechar(); onCompleta(); }}>Ver explicação completa</button>}
    </span>}
  </span>;
}
