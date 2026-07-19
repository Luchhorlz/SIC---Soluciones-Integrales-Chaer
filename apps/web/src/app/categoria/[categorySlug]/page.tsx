import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PublicFooter, PublicHeader } from "@/components/public-header";
import { PublicSearchForm } from "@/components/public-search-form";
import { findCategory, getPublicCatalog } from "@/lib/public-catalog";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ categorySlug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { categorySlug } = await params;
  const category = findCategory(await getPublicCatalog(), categorySlug);
  if (!category) return {};
  return { title: `${category.name} | SIC`, description: category.description ?? `Servicios de ${category.name} en SIC.`, alternates: { canonical: `/categoria/${category.slug}` } };
}

export default async function CategoryPage({ params }: Props) {
  const { categorySlug } = await params;
  const category = findCategory(await getPublicCatalog(), categorySlug);
  if (!category) notFound();
  return (
    <main><PublicHeader />
      <section className="catalog-hero inner"><div className="public-breadcrumbs"><Link href="/servicios">Servicios</Link><span>›</span><b>{category.name}</b></div><p className="eyebrow">CATEGORÍA {String(category.position).padStart(2, "0")}</p><h1>{category.name}</h1><p>{category.description ?? "Elegí una subcategoría para ver todos los servicios disponibles."}</p><PublicSearchForm compact /></section>
      <section className="subcategory-directory">
        {category.subcategories.map((subcategory) => <article key={subcategory.slug}><div><span>{subcategory.services.length}</span><small>servicios</small></div><h2><Link href={`/categoria/${category.slug}/${subcategory.slug}`}>{subcategory.name}</Link></h2><p>{subcategory.description ?? "Opciones incluidas en el catálogo SIC."}</p><ul>{subcategory.services.slice(0, 5).map((service) => <li key={service.slug}><Link href={`/servicio/${service.slug}`}>{service.name}</Link></li>)}</ul><Link className="catalog-more" href={`/categoria/${category.slug}/${subcategory.slug}`}>Ver todos →</Link></article>)}
      </section>
      <PublicFooter />
    </main>
  );
}
