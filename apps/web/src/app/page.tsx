import Link from "next/link";

import { ProviderResultCard } from "@/components/provider-result-card";
import { PublicFooter, PublicHeader } from "@/components/public-header";
import { PublicSearchForm } from "@/components/public-search-form";
import { getPublicCatalog } from "@/lib/public-catalog";
import { searchProviders } from "@/lib/public-search";

export const dynamic = "force-dynamic";

const categoryIcons = ["⌂", "⚒", "⌁", "✦", "◈", "▣", "◇", "◎"];

export default async function Home() {
  const [catalog, featured] = await Promise.all([getPublicCatalog(), searchProviders({ mode: "REMOTE", limit: 4 })]);
  const categories = catalog.categories.slice(0, 8);
  return (
    <main>
      <PublicHeader />
      <section className="hero" id="inicio">
        <div className="hero-copy">
          <p className="eyebrow">SERVICIOS CONFIABLES, CUANDO LOS NECESITÁS</p>
          <h1>Encontrá el servicio que necesitás, <span>cerca tuyo o a distancia</span></h1>
          <p className="lead">Explorá el catálogo completo y encontrá prestadores que cumplen las reglas de visibilidad de SIC.</p>
          <PublicSearchForm />
          <div className="trust-row">
            <div><b>✓ Visibilidad verificada</b><span>Cuenta, perfil y suscripción</span></div>
            <div><b>☆ Información transparente</b><span>Modalidad y cobertura</span></div>
            <div><b>◷ Privacidad geográfica</b><span>Sin domicilios públicos</span></div>
          </div>
        </div>
        <div className="hero-visual" aria-label="Servicios presenciales y remotos conectados por SIC">
          <div className="orbit orbit-one">⚒</div><div className="orbit orbit-two">⌁</div><div className="orbit orbit-three">✦</div>
          <div className="person worker"><span>SIC</span></div><div className="person client"><span>24</span></div>
          <div className="visual-caption">Catálogo real: 1.392 servicios</div>
        </div>
      </section>

      <section className="section" id="servicios">
        <div className="section-heading"><div><p className="eyebrow">EXPLORÁ SIC</p><h2>Categorías destacadas</h2></div><Link href="/servicios">Ver las 29 categorías →</Link></div>
        <div className="category-grid">
          {categories.map((category, index) => <Link className="category-card" href={`/categoria/${category.slug}`} key={category.slug}><span>{categoryIcons[index]}</span><b>{category.name}</b><small>{category.subcategories.length} subcategorías</small></Link>)}
        </div>
      </section>

      <section className="section providers" id="prestadores">
        <div className="section-heading"><div><p className="eyebrow">PRESTADORES VISIBLES</p><h2>Opciones remotas destacadas</h2></div><Link href="/buscar?q=asesoramiento&mode=REMOTE">Explorar búsqueda →</Link></div>
        {featured.results.length ? <div className="home-provider-list">{featured.results.map((result) => <ProviderResultCard result={result} key={result.provider_slug} />)}</div> : <div className="public-empty-state"><span>⌕</span><h3>Todavía no hay prestadores públicos para destacar</h3><p>El catálogo ya se puede explorar completo. Los perfiles aparecerán aquí sólo cuando estén aprobados, documentados y con suscripción habilitada.</p></div>}
      </section>

      <section className="coming" id="como-funciona">
        <div><p className="eyebrow">BÚSQUEDA FUNCIONAL</p><h2>Buscá, filtrá y compará con privacidad.</h2><p>Podés navegar las 29 categorías, buscar cualquiera de los 1.392 servicios y, si autorizás tu ubicación, filtrar por cobertura aproximada.</p></div>
        <Link className="secondary" href="/servicios">Explorar servicios</Link>
      </section>
      <PublicFooter />
    </main>
  );
}
