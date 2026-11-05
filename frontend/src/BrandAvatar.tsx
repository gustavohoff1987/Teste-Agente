import agente from "./assets/agente.png";

/** Personagem do agente: o desenho vetorial original (assets/agente.svg), servido como imagem rasterizada (assets/agente.png,
 * 192 × 192 px, renderizada do próprio SVG, sem mudar cor nem traço). Por quê (05/11/2026): os navegadores que escurecem a página
 * sozinhos (o escurecimento automático do Chrome, o modo escuro forçado das WebViews de alguns aplicativos e de alguns
 * navegadores de celular) recolorem todo conteúdo vetorial, o SVG embutido ou como imagem, e ignoram as declarações de exclusão
 * (color-scheme: only light): o cabelo ficava claro e a pele, pálida, e o personagem parecia esmaecido. Uma imagem rasterizada não
 * é recolorida por eles, e o personagem aparece com as cores originais no claro, no escuro e no escurecimento forçado. Sem imagens
 * remotas: o arquivo vai junto com a página (o Vite resolve o caminho, inclusive no GitHub Pages). */
type Props = { className?: string; size?: number };
export default function BrandAvatar({ className = "", size = 42 }: Props) {
  return <img src={agente} width={size} height={size} alt="Jovem negro de óculos e jaleco, em estilo de animação"
    className={"marca-personagem" + (className ? " " + className : "")} data-testid="marca-personagem" decoding="async"
    draggable={false}/>;
}
