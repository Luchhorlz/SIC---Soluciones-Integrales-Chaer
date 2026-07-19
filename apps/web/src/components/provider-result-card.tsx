import Image from "next/image";
import Link from "next/link";

import { demoProviderImage } from "@/lib/demo-visuals";
import { formatOfferPrice, modalityLabel, type ProviderResult } from "@/lib/public-search-types";

function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

export function ProviderResultCard({ result }: { result: ProviderResult }) {
  const { offer } = result;
  return (
    <article className="search-result-card">
      <div className={`search-result-avatar${result.is_demo ? " has-photo" : ""}`} aria-hidden="true">
        {result.is_demo ? <Image src={demoProviderImage(result.provider_slug)} alt="" width={184} height={224} sizes="(max-width: 700px) 62px, 92px" /> : initials(result.display_name)}
      </div>
      <div className="search-result-body">
        <div className="search-result-heading">
          <div><p>{offer.category_name} · {offer.subcategory_name}</p><h2><Link href={`/prestador/${result.provider_slug}`}>{result.display_name}</Link></h2>{result.business_name && <span>{result.business_name}</span>}</div>
          <b>{formatOfferPrice(offer)}</b>
        </div>
        <h3>{offer.headline}</h3>
        <p className="search-result-description">{offer.description}</p>
        <div className="result-badges">
          {result.is_demo && <span className="demo-badge">DEMO · Perfil ficticio</span>}
          {result.is_identity_verified && <span>✓ Identidad verificada</span>}
          {offer.modalities.map((item) => <span key={item}>{modalityLabel(item)}</span>)}
          {offer.available_today && <span>Disponible hoy</span>}
        </div>
        <div className="search-result-meta">
          <span><b>★ {result.rating_average.toFixed(1)}</b> ({result.rating_count})</span>
          <span>{result.completed_services_count} servicios completados</span>
          {offer.distance_meters !== null && <span>Distancia aprox. {(offer.distance_meters / 1000).toLocaleString("es-AR", { maximumFractionDigits: 1 })} km</span>}
          <Link href={`/prestador/${result.provider_slug}`}>Ver perfil →</Link>
        </div>
      </div>
    </article>
  );
}
