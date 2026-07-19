"use client";

import Link from "next/link";
import { useState } from "react";

import { ProviderResultCard } from "@/components/provider-result-card";
import type { ProviderResult } from "@/lib/public-search-types";

function pointPositions(results: ProviderResult[]) {
  const located = results.filter((item) => item.offer.approximate_latitude !== null && item.offer.approximate_longitude !== null);
  if (!located.length) return [];
  const latitudes = located.map((item) => item.offer.approximate_latitude as number);
  const longitudes = located.map((item) => item.offer.approximate_longitude as number);
  const minLatitude = Math.min(...latitudes);
  const maxLatitude = Math.max(...latitudes);
  const minLongitude = Math.min(...longitudes);
  const maxLongitude = Math.max(...longitudes);
  return located.map((item, index) => ({
    item,
    left: 12 + (((item.offer.approximate_longitude as number) - minLongitude) / (maxLongitude - minLongitude || 1)) * 76,
    top: 12 + ((maxLatitude - (item.offer.approximate_latitude as number)) / (maxLatitude - minLatitude || 1)) * 72,
    index: index + 1,
  }));
}

export function SearchResultsView({ results }: { results: ProviderResult[] }) {
  const [view, setView] = useState<"list" | "map">("list");
  const points = pointPositions(results);
  return (
    <>
      <div className="mobile-result-tabs" role="group" aria-label="Vista de resultados">
        <button className={view === "list" ? "active" : ""} type="button" onClick={() => setView("list")}>Lista</button>
        <button className={view === "map" ? "active" : ""} type="button" onClick={() => setView("map")}>Mapa</button>
      </div>
      <div className={`search-results-layout mobile-${view}`}>
        <section className="search-result-list" aria-label="Prestadores encontrados">
          {results.map((result) => <ProviderResultCard result={result} key={`${result.provider_slug}:${result.offer.id}`} />)}
        </section>
        <aside className="public-map" aria-label="Mapa de ubicaciones aproximadas">
          <div className="public-map-grid" />
          <div className="public-map-notice"><b>Ubicaciones aproximadas</b><span>SIC no publica domicilios ni coordenadas exactas.</span></div>
          {points.map(({ item, left, top, index }) => <Link className="public-map-pin" style={{ left: `${left}%`, top: `${top}%` }} href={`/prestador/${item.provider_slug}`} key={item.provider_slug} aria-label={`Ver a ${item.display_name}`}><span>{index}</span></Link>)}
          {!points.length && <div className="public-map-empty"><span>⌖</span><b>No hay resultados presenciales ubicados</b><p>Las opciones remotas se muestran únicamente en la lista.</p></div>}
        </aside>
      </div>
    </>
  );
}
