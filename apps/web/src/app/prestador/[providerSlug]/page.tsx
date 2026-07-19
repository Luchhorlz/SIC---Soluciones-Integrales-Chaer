import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { toggleFavorite } from "@/app/favorite-actions";
import { auth } from "@/auth";
import { PublicFooter, PublicHeader } from "@/components/public-header";
import { isApplicationAuthConfigured } from "@/lib/auth-config";
import { demoProviderImage } from "@/lib/demo-visuals";
import { getClientFavorites, getPublicReviews } from "@/lib/internal-api";
import { formatOfferPrice, getPublicProvider, modalityLabel } from "@/lib/public-search";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ providerSlug: string }> };

function initials(name: string) { return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase(); }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { providerSlug } = await params;
  const { profile } = await getPublicProvider(providerSlug);
  if (!profile) return { robots: { index: false, follow: false } };
  return { title: `${profile.display_name} | Prestador SIC`, description: profile.bio ?? `Perfil público verificado de ${profile.display_name} en SIC.`, alternates: { canonical: `/prestador/${profile.slug}` }, robots: profile.is_demo ? { index: false, follow: false } : undefined, openGraph: { title: `${profile.display_name} | SIC`, description: profile.bio ?? "Prestador visible en SIC." } };
}

export default async function ProviderPage({ params }: Props) {
  const { providerSlug } = await params;
  const [{ profile, apiUnavailable }, reviews] = await Promise.all([getPublicProvider(providerSlug), getPublicReviews(providerSlug)]);
  if (!profile && !apiUnavailable) notFound();
  if (!profile) return <main><PublicHeader /><section className="public-unavailable"><span>◷</span><h1>El perfil no se puede consultar ahora</h1><p>La base local de prestadores no está conectada en esta previsualización. No se expone información alternativa ni almacenada en el navegador.</p><Link className="secondary" href="/servicios">Explorar catálogo</Link></section><PublicFooter /></main>;
  const configured = isApplicationAuthConfigured();
  const session = configured ? await auth() : null;
  let favorite = false;
  if (session?.user?.roles.includes("CLIENT")) { try { favorite = (await getClientFavorites({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId })).some((item) => item.provider_slug === profile.slug); } catch { favorite = false; } }
  const jsonLd = { "@context": "https://schema.org", "@type": "ProfessionalService", name: profile.business_name ?? profile.display_name, description: profile.bio, aggregateRating: profile.rating_count ? { "@type": "AggregateRating", ratingValue: profile.rating_average, reviewCount: profile.rating_count } : undefined };
  return (
    <main><PublicHeader />
      <section className="public-profile-hero"><div className="public-breadcrumbs"><Link href="/buscar">Prestadores</Link><span>›</span><b>Perfil público</b></div>{profile.is_demo && <div className="demo-profile-banner"><b>Perfil demostrativo</b><span>La identidad, experiencia, calificaciones y documentación de este perfil son ficticias.</span></div>}<div className="profile-hero-grid"><div className={`profile-public-avatar${profile.is_demo ? " has-photo" : ""}`}>{profile.is_demo ? <Image src={demoProviderImage(profile.slug)} alt={`Retrato ilustrativo de ${profile.display_name}`} width={300} height={356} priority /> : initials(profile.display_name)}</div><div><div className="profile-public-badges">{profile.is_identity_verified && <span>✓ Identidad verificada</span>}{profile.documents_verified && <span>✓ Documentación habilitante</span>}{profile.is_demo && <span className="demo-badge">DEMO · Datos ficticios</span>}</div><h1>{profile.display_name}</h1>{profile.business_name && <h2>{profile.business_name}</h2>}<p>{profile.bio ?? "Este prestador todavía no agregó una presentación pública."}</p><div className="profile-public-stats"><span><b>★ {profile.rating_average.toFixed(1)}</b><small>{profile.rating_count} calificaciones</small></span><span><b>{profile.completed_services_count}</b><small>servicios completados</small></span><span><b>{Math.round(profile.response_rate)}%</b><small>tasa de respuesta</small></span>{profile.experience_years !== null && <span><b>{profile.experience_years}</b><small>años de experiencia</small></span>}</div></div><aside><b>Contratación privada</b><p>Elegí una oferta para enviarle al prestador los detalles y, si corresponde, pedir presupuesto.</p>{profile.services[0] ? <Link className="primary" href={`/solicitar/${profile.slug}/${profile.services[0].id}`}>Solicitar servicio</Link> : <span>Sin ofertas disponibles</span>}<form action={toggleFavorite}><input type="hidden" name="provider_slug" value={profile.slug} /><input type="hidden" name="return_path" value={`/prestador/${profile.slug}`} /><button className="profile-favorite-button" name="favorite" value={String(!favorite)}>{favorite ? "♥ Guardado en favoritos" : "♡ Guardar favorito"}</button></form><small>Tu dirección exacta nunca se publica y sólo se comparte dentro de una contratación confirmada.</small></aside></div></section>

      <div className="public-profile-content">
        <section><div className="section-heading"><div><p className="eyebrow">SERVICIOS</p><h2>Ofertas visibles</h2></div></div><div className="profile-offer-list">{profile.services.map((offer) => <article key={offer.id}><div><p>{offer.category_name} · {offer.subcategory_name}</p><h3><Link href={`/servicio/${offer.service_slug}`}>{offer.headline}</Link></h3><span>{offer.service_name}</span></div><b>{formatOfferPrice(offer)}</b><p>{offer.description}</p><div>{offer.modalities.map((modality) => <span key={modality}>{modalityLabel(modality)}</span>)}{offer.available_today && <span>Disponible hoy</span>}<Link className="offer-request-link" href={`/solicitar/${profile.slug}/${offer.id}`}>Solicitar esta oferta</Link></div></article>)}</div></section>
        <aside><section className="profile-public-card"><p className="eyebrow">VERIFICACIONES</p><h2>Información visible</h2><ul><li><b>Identidad</b><span>{profile.is_identity_verified ? "Verificada" : "No informada"}</span></li><li><b>Documentación del servicio</b><span>{profile.documents_verified ? "Vigente" : "No informada"}</span></li><li><b>Perfil completo</b><span>{profile.profile_completeness}%</span></li></ul><p className="privacy-copy">La dirección y las coordenadas exactas del prestador nunca se publican.</p></section></aside>
        {profile.portfolio.length > 0 && <section className="profile-portfolio"><div className="section-heading"><div><p className="eyebrow">TRABAJOS</p><h2>Experiencia compartida</h2></div></div><div>{profile.portfolio.map((item) => <article key={`${item.position}:${item.title}`}><span>{String(item.position + 1).padStart(2, "0")}</span><h3>{item.title}</h3><p>{item.description}</p></article>)}</div></section>}
        <section className="profile-reviews"><div className="section-heading"><div><p className="eyebrow">OPINIONES VERIFICADAS</p><h2>Experiencias publicadas</h2></div><span>{reviews.length}</span></div>{reviews.length ? <div>{reviews.map((review) => <article key={review.id}><div><b>{"★".repeat(review.rating)}{"☆".repeat(5 - review.rating)}</b><small>{new Intl.DateTimeFormat("es-AR", { dateStyle: "medium" }).format(new Date(review.published_at))}</small></div><p>{review.comment}</p><span>Contratación verificada · {review.service_name}</span></article>)}</div> : <div className="profile-review-empty">Este prestador todavía no tiene opiniones publicadas.</div>}</section>
      </div>
      {!profile.is_demo && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }} />}
      <PublicFooter />
    </main>
  );
}
