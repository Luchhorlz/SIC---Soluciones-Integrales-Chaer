import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ProviderResultCard } from "@/components/provider-result-card";
import { PublicFooter, PublicHeader } from "@/components/public-header";
import { PublicSearchForm } from "@/components/public-search-form";
import { findService, getPublicCatalog } from "@/lib/public-catalog";
import { searchProviders } from "@/lib/public-search";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ serviceSlug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { serviceSlug } = await params;
  const match = findService(await getPublicCatalog(), serviceSlug);
  if (!match) return {};
  return { title: `${match.service.name} | SIC`, description: match.service.description ?? `Encontrá prestadores para ${match.service.name} en SIC.`, alternates: { canonical: `/servicio/${serviceSlug}` }, openGraph: { title: `${match.service.name} | SIC`, description: `Prestadores visibles para ${match.service.name}.` } };
}

export default async function ServicePage({ params }: Props) {
  const { serviceSlug } = await params;
  const match = findService(await getPublicCatalog(), serviceSlug);
  if (!match) notFound();
  const providers = await searchProviders({ service_slug: serviceSlug, mode: "REMOTE", limit: 12 });
  const jsonLd = { "@context": "https://schema.org", "@type": "Service", name: match.service.name, category: match.subcategory.name, areaServed: "Argentina", provider: { "@type": "Organization", name: "SIC — Soluciones Integrales Chaer" } };
  return (
    <main><PublicHeader />
      <section className="service-detail-hero"><div className="public-breadcrumbs"><Link href="/servicios">Servicios</Link><span>›</span><Link href={`/categoria/${match.category.slug}`}>{match.category.name}</Link><span>›</span><Link href={`/categoria/${match.category.slug}/${match.subcategory.slug}`}>{match.subcategory.name}</Link></div><p className="eyebrow">SERVICIO DEL CATÁLOGO SIC</p><h1>{match.service.name}</h1><p>{match.service.description ?? "Buscá prestadores habilitados para este servicio, de forma presencial o remota según corresponda."}</p><div className="service-capabilities">{match.service.allows_quote && <span>Presupuesto disponible</span>}{match.service.allows_fixed_price && <span>Puede admitir precio informado</span>}{match.service.allows_urgent && <span>Puede admitir urgencias</span>}</div></section>
      <section className="service-provider-search"><div><p className="eyebrow">ENCONTRÁ PRESTADORES</p><h2>Filtrá por modalidad y cobertura</h2><p>Sin ubicación se muestran opciones remotas. Para servicios presenciales, activá tu ubicación aproximada.</p></div><PublicSearchForm initialQuery={match.service.name} initialMode="ALL" compact /></section>
      <section className="service-provider-results"><div className="section-heading"><div><p className="eyebrow">OPCIONES PÚBLICAS</p><h2>Prestadores remotos visibles</h2></div></div>{providers.results.length ? <div className="home-provider-list">{providers.results.map((result) => <ProviderResultCard result={result} key={result.provider_slug} />)}</div> : <div className="public-empty-state"><span>◎</span><h3>No hay prestadores remotos visibles para este servicio</h3><p>Podés usar el buscador superior y autorizar tu ubicación para consultar cobertura presencial.</p></div>}</section>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }} />
      <PublicFooter />
    </main>
  );
}
