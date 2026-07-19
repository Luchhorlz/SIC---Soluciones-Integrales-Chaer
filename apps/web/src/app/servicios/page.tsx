import type { Metadata } from "next";
import Link from "next/link";

import { PublicFooter, PublicHeader } from "@/components/public-header";
import { PublicSearchForm } from "@/components/public-search-form";
import { getPublicCatalog } from "@/lib/public-catalog";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Servicios | SIC", description: "Explorá las 29 categorías y el catálogo completo de servicios de SIC.", alternates: { canonical: "/servicios" } };

export default async function ServicesPage() {
  const catalog = await getPublicCatalog();
  const total = catalog.categories.reduce((count, category) => count + category.subcategories.reduce((subtotal, subcategory) => subtotal + subcategory.services.length, 0), 0);
  return (
    <main><PublicHeader />
      <section className="catalog-hero"><p className="eyebrow">CATÁLOGO SIC</p><h1>¿Qué necesitás resolver?</h1><p>Elegí una categoría o buscá directamente entre {total.toLocaleString("es-AR")} servicios.</p><PublicSearchForm compact /></section>
      <section className="public-catalog-shell">
        <aside><b>29 categorías</b><p>La lista completa proviene del catálogo canónico aprobado.</p>{catalog.categories.map((category) => <Link href={`/categoria/${category.slug}`} key={category.slug}>{category.name}<span>{category.subcategories.length}</span></Link>)}</aside>
        <div className="public-category-directory">
          {catalog.categories.map((category) => <article id={category.slug} key={category.slug}><div className="catalog-card-icon">{String(category.position).padStart(2, "0")}</div><div><h2><Link href={`/categoria/${category.slug}`}>{category.name}</Link></h2><p>{category.description ?? `${category.subcategories.length} grupos de servicios disponibles.`}</p><div>{category.subcategories.slice(0, 6).map((subcategory) => <Link href={`/categoria/${category.slug}/${subcategory.slug}`} key={subcategory.slug}>{subcategory.name}</Link>)}</div>{category.subcategories.length > 6 && <Link className="catalog-more" href={`/categoria/${category.slug}`}>Ver todas las subcategorías →</Link>}</div></article>)}
        </div>
      </section>
      <PublicFooter />
    </main>
  );
}
