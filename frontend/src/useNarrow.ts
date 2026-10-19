import { useEffect, useState } from "react";

/** Tela estreita (celular, abaixo de 640 px): as listas de barras, valores, halteres e pirulitos põem o nome do território
 * numa linha própria, inteiro, e o desenho e o valor na linha de baixo. Só layout; nada muda nos valores. */
export function useNarrow(): boolean {
  const query = "(max-width: 639px)";
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && !!window.matchMedia && window.matchMedia(query).matches);
  useEffect(() => {
    if (!window.matchMedia) return;
    const media = window.matchMedia(query);
    const update = () => setNarrow(media.matches);
    update();
    media.addEventListener?.("change", update);
    return () => media.removeEventListener?.("change", update);
  }, []);
  return narrow;
}
