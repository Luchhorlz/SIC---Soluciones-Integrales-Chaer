import type { Metadata } from "next";
import Link from "next/link";

import { PublicFooter, PublicHeader } from "@/components/public-header";
import { PublicSearchForm } from "@/components/public-search-form";
import { SearchResultsView } from "@/components/search-results-view";
import { getPublicCatalog, searchCatalog } from "@/lib/public-catalog";
import { searchProviders, type SearchMode, type SearchSort } from "@/lib/public-search";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Buscar servicios y prestadores | SIC", description: "Buscá servicios y prestadores visibles por modalidad y cobertura aproximada.", alternates: { canonical: "/buscar" }, robots: { index: false, follow: true } };

type Params = Record<string, string | string[] | undefined>;
type Props = { searchParams: Promise<Params> };
const validModes = new Set<SearchMode>(["ALL", "NEARBY", "REMOTE", "HYBRID", "AT_PROVIDER_LOCATION", "PICKUP_DELIVERY"]);
const validSorts = new Set<SearchSort>(["RELEVANCE", "RATING", "DISTANCE"]);

function single(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }
function numberValue(value: string | undefined) { const parsed = value === undefined ? undefined : Number(value); return Number.isFinite(parsed) ? parsed : undefined; }

function searchLink(params: URLSearchParams, changes: Record<string, string | undefined>) {
  const next = new URLSearchParams(params);
  for (const [key, value] of Object.entries(changes)) {
    if (value === undefined) next.delete(key);
    else next.set(key, value);
  }
  next.delete("cursor");
  return `/buscar?${next}`;
}

export default async function SearchPage({ searchParams }: Props) {
  const raw = await searchParams;
  const q = (single(raw.q) ?? "").trim();
  const requestedMode = validModes.has(single(raw.mode) as SearchMode) ? single(raw.mode) as SearchMode : "ALL";
  const latitude = numberValue(single(raw.latitude));
  const longitude = numberValue(single(raw.longitude));
  const hasLocation = latitude !== undefined && longitude !== undefined;
  const locationRequired = ["NEARBY", "HYBRID", "AT_PROVIDER_LOCATION", "PICKUP_DELIVERY"].includes(requestedMode) && !hasLocation;
  const mode: SearchMode = locationRequired ? "ALL" : requestedMode;
  const requestedSort = validSorts.has(single(raw.sort) as SearchSort) ? single(raw.sort) as SearchSort : "RELEVANCE";
  const sort: SearchSort = requestedSort === "DISTANCE" && !hasLocation ? "RELEVANCE" : requestedSort;
  const availableToday = single(raw.available_today) === "true";
  const cursor = single(raw.cursor);
  const parameters = new URLSearchParams();
  for (const [key, value] of Object.entries(raw)) if (typeof value === "string") parameters.set(key, value);

  const [catalog, providers] = await Promise.all([
    getPublicCatalog(),
    q.length >= 2 || single(raw.service_slug) || single(raw.category_slug) || single(raw.subcategory_slug)
      ? searchProviders({ q: q.length >= 2 ? q : undefined, service_slug: single(raw.service_slug), category_slug: single(raw.category_slug), subcategory_slug: single(raw.subcategory_slug), mode, latitude, longitude, radius_meters: numberValue(single(raw.radius_meters)), available_today: availableToday, sort, cursor, limit: 20 })
      : Promise.resolve({ results: [], count: 0, next_cursor: null, mode, location_applied: hasLocation, apiUnavailable: false, demoData: false }),
  ]);
  const catalogMatches = q.length >= 2 ? searchCatalog(catalog, q) : [];

  return (
    <main><PublicHeader />
      <section className="search-page-header"><div><div className="public-breadcrumbs"><Link href="/">Inicio</Link><span>›</span><b>Buscar</b></div><h1>{q ? <>Resultados para <span>“{q}”</span></> : "Buscá un servicio"}</h1><p>{q ? `${catalogMatches.length} coincidencias del catálogo · ${providers.count} prestadores visibles` : "Escribí el servicio que necesitás para consultar el catálogo completo."}</p></div><PublicSearchForm initialQuery={q} initialMode={requestedMode} initialLatitude={latitude?.toString()} initialLongitude={longitude?.toString()} compact /></section>

      {q && <section className="catalog-match-strip"><div className="section-heading"><div><p className="eyebrow">CATÁLOGO SIC</p><h2>Servicios que coinciden</h2></div>{catalogMatches.length > 0 && <span>{catalogMatches.length} mostrados</span>}</div>{catalogMatches.length ? <div>{catalogMatches.map(({ category, subcategory, service }) => <Link href={`/servicio/${service.slug}`} key={service.slug}><b>{service.name}</b><span>{category.name} · {subcategory.name}</span></Link>)}</div> : <p className="catalog-no-match">No encontramos un nombre igual en el catálogo. Probá con otra palabra o explorá las <Link href="/servicios">29 categorías</Link>.</p>}</section>}

      {(q || single(raw.service_slug) || single(raw.category_slug)) && <section className="provider-search-section">
        <div className="search-filter-bar">
          <div className="filter-pills" aria-label="Modalidad">
            <Link className={requestedMode === "ALL" ? "active" : ""} href={searchLink(parameters, { mode: "ALL" })}>Todos</Link>
            <Link className={requestedMode === "NEARBY" ? "active" : ""} href={searchLink(parameters, { mode: "NEARBY" })}>Cerca mío</Link>
            <Link className={requestedMode === "REMOTE" ? "active" : ""} href={searchLink(parameters, { mode: "REMOTE" })}>Remoto</Link>
            <Link className={requestedMode === "HYBRID" ? "active" : ""} href={searchLink(parameters, { mode: "HYBRID" })}>Híbrido</Link>
          </div>
          <div className="filter-pills secondary-pills">
            <Link className={availableToday ? "active" : ""} href={searchLink(parameters, { available_today: availableToday ? undefined : "true" })}>Disponible hoy</Link>
            <Link className={sort === "RATING" ? "active" : ""} href={searchLink(parameters, { sort: sort === "RATING" ? "RELEVANCE" : "RATING" })}>Mejor calificados</Link>
            {hasLocation && <Link className={sort === "DISTANCE" ? "active" : ""} href={searchLink(parameters, { sort: sort === "DISTANCE" ? "RELEVANCE" : "DISTANCE" })}>Menor distancia</Link>}
          </div>
        </div>
        {locationRequired && <div className="public-search-notice">⌖ Para usar este filtro, activá tu ubicación aproximada en el buscador. Mientras tanto mostramos únicamente opciones remotas.</div>}
        {providers.demoData && <div className="demo-catalog-notice"><b>Resultados de demostración</b><span>SIC está mostrando perfiles ficticios claramente marcados. Hay tres identidades demo distintas para cada servicio del catálogo.</span></div>}
        {providers.apiUnavailable && <div className="public-search-notice warning">El catálogo está disponible, pero la base local de prestadores no está conectada en esta previsualización.</div>}
        {providers.results.length ? <><div className="search-count"><b>{providers.count} prestadores visibles</b><span>Lista y mapa usan exactamente los mismos resultados.</span></div><SearchResultsView results={providers.results} />{providers.next_cursor && <Link className="secondary search-more" href={searchLink(parameters, { cursor: providers.next_cursor })}>Ver más resultados</Link>}</> : <div className="public-empty-state search-empty"><span>◎</span><h3>No hay prestadores visibles para estos filtros</h3><p>Esto no oculta el catálogo: los servicios encontrados siguen arriba. Probá “Remoto”, quitá “Disponible hoy” o activá tu ubicación para consultar cobertura.</p></div>}
      </section>}
      <PublicFooter />
    </main>
  );
}
