/** Identidade visual própria: profissional estilizado de óculos e estetoscópio.
 * Elemento SVG vetorial, sem fontes, rede ou dependências externas.
 */
type Props = { className?: string; size?: number; dark?: boolean };
export default function BrandAvatar({className = "", size = 42, dark = true}: Props) {
  const ink = dark ? "#061a2d" : "#ffffff";
  return <svg className={className} width={size} height={size} viewBox="0 0 64 64"
    fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Profissional de saúde com óculos">
    <path d="M19 24v-6C19 8 25 5 32 5s13 3 13 13v6l-3 5H22l-3-5Z" fill={ink}/>
    <path d="M22 29c1 10 5 15 10 15s9-5 10-15" stroke={ink} strokeWidth="3.5" strokeLinecap="round"/>
    <path d="M19 24h10a4 4 0 0 1 4 4 4 4 0 0 1 4-4h9" stroke={ink} strokeWidth="3.6" strokeLinecap="round"/>
    <rect x="18" y="23" width="14" height="9" rx="3.5" stroke={ink} strokeWidth="3"/>
    <rect x="34" y="23" width="14" height="9" rx="3.5" stroke={ink} strokeWidth="3"/>
    <path d="M23 43 12 48a12 12 0 0 0-6 10v3h52v-3a12 12 0 0 0-6-10l-11-5-9 8-9-8Z" fill={ink}/>
    <path d="M27 47 32 52l5-5M32 52v10" stroke="#fff" strokeWidth="2.4" strokeLinecap="round"/>
    <path d="M17 51v5a5 5 0 0 0 10 0v-4M47 51v4" stroke="#fff" strokeWidth="2.4" strokeLinecap="round"/>
    <circle cx="47" cy="57" r="3" fill="#fff"/>
    <circle cx="47" cy="57" r="1.5" fill={ink}/>
  </svg>;
}
