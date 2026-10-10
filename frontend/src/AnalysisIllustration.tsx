import type { ReactNode } from "react";

/** Ilustrações vetoriais em duas cores para as dez capacidades. */
export default function AnalysisIllustration({ kind }: { kind: string }) {
  const drawings: Record<string, ReactNode> = {
    density: <><path d="m19 28 17-6 24 8 17-6v43l-17 7-24-8-17 6Z" fill="currentColor" fillOpacity=".09"/><path d="m19 28 17-6 24 8 17-6v43l-17 7-24-8-17 6Zm17-6v44m24-36v44"/><circle cx="48" cy="36" r="7" fill="var(--card-soft)"/><path d="M35 57c0-13 26-13 26 0" fill="var(--card-soft)"/><circle cx="69" cy="61" r="13" fill="var(--card-accent)" stroke="white"/><path d="M63 61h12m-6-6v12" stroke="white"/></>,
    counts: <><circle cx="48" cy="30" r="10" fill="currentColor" fillOpacity=".13"/><circle cx="25" cy="38" r="7"/><circle cx="71" cy="38" r="7"/><path d="M29 73v-8c0-22 38-22 38 0v8Z" fill="currentColor" fillOpacity=".13"/><path d="M15 66v-8c0-8 9-13 17-8m49 16v-8c0-8-9-13-17-8"/><path d="M40 59v9m16-9v9"/></>,
    distribution: <><path d="M19 20v55h61"/><rect x="29" y="48" width="10" height="19" rx="3" fill="currentColor" fillOpacity=".18"/><rect x="46" y="32" width="10" height="35" rx="3" fill="currentColor" fillOpacity=".35"/><rect x="63" y="20" width="10" height="47" rx="3" fill="currentColor" fillOpacity=".65"/><path d="M29 38 49 22l19-10" strokeDasharray="3 5"/></>,
    comparisons: <><rect x="15" y="26" width="27" height="43" rx="7" fill="currentColor" fillOpacity=".09"/><rect x="54" y="26" width="27" height="43" rx="7" fill="currentColor" fillOpacity=".22"/><path d="M24 39h9m-9 10h9m30-10h9m-9 10h9M30 16h34l-5-5m5 5-5 5M66 80H32l5-5m-5 5 5 5"/></>,
    temporal: <><path d="M18 23v52h61"/><path d="m27 62 15-18 15 6 20-26v43H27Z" fill="currentColor" fillOpacity=".12" stroke="none"/><path d="m27 62 15-18 15 6 20-26m-12 0h12v12" strokeWidth="3.5"/><circle cx="42" cy="44" r="4" fill="var(--card-soft)"/><circle cx="57" cy="50" r="4" fill="var(--card-soft)"/></>,
    aggregate: <><path d="m15 60 33 17 33-17-33-17Z" fill="currentColor" fillOpacity=".1"/><path d="m15 46 33 17 33-17-33-17Z" fill="var(--card-soft)"/><path d="m15 32 33 17 33-17-33-17Z" fill="currentColor" fillOpacity=".2"/><path d="m33 32 15 8 15-8"/></>,
    spatial: <><path d="m18 66 20-19 20 14 20-33" strokeDasharray="4 6"/><path d="M59 33c0 12-12 24-12 24S35 45 35 33a12 12 0 0 1 24 0Z" fill="currentColor" fillOpacity=".18"/><circle cx="47" cy="33" r="4"/><circle cx="18" cy="66" r="6" fill="var(--card-soft)"/><circle cx="58" cy="61" r="5" fill="var(--card-soft)"/><circle cx="78" cy="28" r="6" fill="var(--card-soft)"/><path d="M31 77h33"/></>,
    ranking: <><path d="M18 49h20v27H18Zm20-17h20v44H38Zm20 26h20v18H58Z" fill="currentColor" fillOpacity=".15"/><path d="m48 11 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1Z" fill="currentColor" fillOpacity=".3"/><path d="M48 43v20m-5-16 5-4M25 60h6m33 8h7"/></>,
    rotation: <><path d="M23 39a27 27 0 0 1 49-8m-1-13 2 14-14-1M73 57a27 27 0 0 1-49 8m1 13-2-14 14 1"/><circle cx="48" cy="40" r="8" fill="currentColor" fillOpacity=".15"/><path d="M34 64v-5c0-14 28-14 28 0v5Z" fill="currentColor" fillOpacity=".15"/></>,
    report: <><path d="M25 15h33l14 14v49H25Z" fill="currentColor" fillOpacity=".09"/><path d="M58 15v15h14M35 40h25m-25 8h13"/><path d="M36 65v-8m10 8V54m10 11V49" strokeWidth="5"/><circle cx="73" cy="71" r="12" fill="var(--card-accent)" stroke="white"/><path d="m68 71 4 4 6-8" stroke="white"/></>,
  };
  return <svg viewBox="0 0 96 96" fill="none" stroke="currentColor" strokeWidth="2.5"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {drawings[kind]}
  </svg>;
}
