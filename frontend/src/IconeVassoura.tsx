import type { SVGProps } from "react";

/** Vassoura (24/10/2026): o ícone do "Limpar" na Seleção de Territórios e nas análises, no traço dos ícones da interface
 * (24 × 24, contorno de 2 px, cantos arredondados), porque a biblioteca de ícones instalada não traz uma vassoura. */
export default function IconeVassoura({ size = 16, ...resto }: { size?: number } & SVGProps<SVGSVGElement>) {
  return <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...resto}>
    <path d="M12 2v7"/>
    <path d="M8 9h8a1 1 0 0 1 1 1v3H7v-3a1 1 0 0 1 1-1z"/>
    <path d="M7 13 5.2 20.8A1 1 0 0 0 6.2 22h11.6a1 1 0 0 0 1-1.2L17 13"/>
    <path d="m9.5 17-.5 5"/>
    <path d="M12 17v5"/>
    <path d="m14.5 17 .5 5"/>
  </svg>;
}
