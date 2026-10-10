/** Personagem vetorial original, sem imagens remotas ou dependências externas. */
type Props = { className?: string; size?: number; dark?: boolean };
export default function BrandAvatar({className = "", size = 42, dark = true}: Props) {
  const frame = dark ? "#172b42" : "#f8fafc";
  return <svg className={className} width={size} height={size} viewBox="0 0 96 96"
    fill="none" xmlns="http://www.w3.org/2000/svg" role="img"
    aria-label="Jovem negro de óculos e jaleco, em estilo de animação" focusable="false">
    <circle cx="48" cy="48" r="46" fill="#e7f3f5"/>
    <path d="M8 89c1-16 9-23 27-27h26c18 4 26 11 27 27v5H8Z" fill="#cbdde7"/>
    <path d="M12 91c2-15 10-22 26-25h20c16 3 24 10 26 25v3H12Z" fill="#f8fcff"/>
    <path d="m35 65 13 7 13-7-6 29H41Z" fill="#236079"/>
    <path d="M39 55h18v12c-2 7-16 7-18 0Z" fill="#895237"/>
    <path d="M39 57c5 6 12 7 18 2v6c-5 4-13 2-18-1Z" fill="#683d2c"/>
    <path d="m37 64 11 9-9 9-8-14ZM59 64l-11 9 9 9 8-14Z" fill="#e0edf3"/>
    <path d="m32 67 9 27H29l3-10-7-5ZM64 67 55 94h12l-3-10 7-5Z" fill="white"/>
    <path d="m46 75-3 5 3 14h4l3-14-3-5Z" fill="#1aa2a5"/>
    <path d="m21 86-1 8m55-8 1 8" stroke="#b5ccd8" strokeWidth="1.5" strokeLinecap="round"/>
    <rect x="65" y="80" width="9" height="8" rx="2" fill="#dbeaf0"/>
    <path d="M68 77v7" stroke="#24969f" strokeWidth="2" strokeLinecap="round"/>
    <path d="M72 78v6" stroke="#42618b" strokeWidth="2" strokeLinecap="round"/>
    <ellipse cx="25" cy="41" rx="6" ry="8" fill="#925637"/>
    <ellipse cx="71" cy="41" rx="6" ry="8" fill="#925637"/>
    <path d="M24 38c3-2 4 1 4 5m44-5c-3-2-4 1-4 5" stroke="#633b2d" strokeWidth="2" strokeLinecap="round"/>
    <path d="M25 29c0-16 46-18 46 0v16c0 16-11 23-23 23S25 61 25 45Z" fill="#a76945"/>
    <path d="M28 32v15c0 11 7 17 18 19-13 0-21-8-21-21V30Z" fill="#824a32"/>
    <path d="M50 24c10 0 16 5 17 13v8c-1 8-4 13-8 16 7-3 12-9 12-17V30Z" fill="#b87950"/>
    <path d="M24 35c-5-6-4-16 0-21 2-7 9-8 14-7 4-6 12-5 16-2 6-3 14 0 15 6 7 2 9 10 5 15l-3 11-5-9c-9 1-15-2-20-6-4 6-12 8-18 7l-1 8Z" fill="#202331"/>
    <path d="M26 19c1-6 7-7 11-4m2-4c4-4 9-3 12 0m5 1c5-2 9 1 9 5M32 24c4 0 7-2 8-5m8-1c4 5 10 6 15 5" stroke="#353848" strokeWidth="3" strokeLinecap="round"/>
    <path d="M31 33c4-2 8-2 11 0m12 0c4-2 8-2 11 0" stroke="#452f2b" strokeWidth="2.2" strokeLinecap="round"/>
    <path d="M30 39c3-3 9-3 12 0m12 0c3-3 9-3 12 0" stroke="#e2b18a" strokeWidth="1.5" strokeLinecap="round"/>
    <ellipse cx="37" cy="41" rx="2.5" ry="3.2" fill="#221f26"/>
    <ellipse cx="59" cy="41" rx="2.5" ry="3.2" fill="#221f26"/>
    <circle cx="38" cy="40" r=".8" fill="white"/>
    <circle cx="60" cy="40" r=".8" fill="white"/>
    <path d="m48 40-2 8c1 2 4 2 6 0" stroke="#7c442f" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
    <rect x="26" y="34" width="19" height="15" rx="6.5" stroke={frame} strokeWidth="3"/>
    <rect x="51" y="34" width="19" height="15" rx="6.5" stroke={frame} strokeWidth="3"/>
    <path d="M45 39c2-2 4-2 6 0M22 36l4 2m44 0 4-2" stroke={frame} strokeWidth="2.5" strokeLinecap="round"/>
    <path d="m29 38 3-2m22 2 3-2" stroke="#f5e8d7" strokeWidth="1.5" strokeLinecap="round" opacity=".7"/>
    <path d="M39 54c5 3 13 3 18-1-2 9-14 10-18 1Z" fill="#633e32"/>
    <path d="M41 55c4 2 10 2 14-1-3 5-10 6-14 1Z" fill="#fff7eb"/>
    <path d="M44 62c3 1 6 1 8-1" stroke="#bf8059" strokeWidth="1.8" strokeLinecap="round"/>
    <path d="M30 70v11c0 7 10 7 10 0v-4m24-7v8" stroke="#44728a" strokeWidth="2.2" strokeLinecap="round"/>
    <circle cx="64" cy="80" r="4" fill="#234b65"/>
    <circle cx="64" cy="80" r="2" fill="#c3e7e7"/>
  </svg>;
}
