import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PublicFooter, PublicHeader } from "@/components/public-header";
import { PublicSearchForm } from "@/components/public-search-form";
import { findCategory, findSubcategory, getPublicCatalog } from "@/lib/public-catalog";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ categorySlug: string; subcategorySlug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { categorySlug, subcategorySlug } = await params;
  const catalog = await getPublicCatalog();
  const item = findSubcategory(catalog, categorySlug, subcategorySlug);
  if (!item) return {};
  return { title: `${item.name} | SIC`, description: `${item.services.length} servicios de ${item.name} en SIC.`, alternates: { canonical: `/categoria/${categorySlug}/${subcategorySlug}` } };
}

export default async function SubcategoryPage({ params }: Props) {
  const { categorySlug, subcategorySlug } = await params;
  const catalog = await getPublicCatalog();
  const category = findCategory(catalog, categorySlug);
  const subcategory = findSubcategory(catalog, categorySlug, subcategorySlug);
  if (!category || !subcategory) notFound();
  return (
    <main><PublicHeader />
      <section className="catalog-hero inner"><div className="public-breadcrumbs"><Link href="/servicios">Servicios</Link><span>›</span><Link href={`/categoria/${category.slug}`}>{category.name}</Link><span>›</span><b>{subcategory.name}</b></div><p className="eyebrow">{subcategory.services.length} SERVICIOS</p><h1>{subcategory.name}</h1><p>{subcategory.description ?? "Seleccioná un servicio para ver su detalle y buscar prestadores visibles."}</p><PublicSearchForm initialQuery={subcategory.name} compact /></section>
      <section className="service-directory"><div className="section-heading"><div><p className="eyebrow">LISTA COMPLETA</p><h2>Servicios disponibles</h2></div></div><div>{subcategory.services.map((service, index) => <Link className="service-directory-card" href={`/servicio/${service.slug}`} key={service.slug}><span>{String(index + 1).padStart(2, "0")}</span><div><h3>{service.name}</h3><p>{service.description ?? "Solicitá información a prestadores habilitados para este servicio."}</p></div><b>Ver servicio →</b></Link>)}</div></section>
      <PublicFooter />
    </main>
  );
}
