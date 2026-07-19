import Link from "next/link";

import { getProviderOffers, type ProviderOffer } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";
import { ProviderShell } from "@/components/provider-shell";

import { toggleProviderProfile } from "../actions";

export const metadata = { title: "Panel del prestador | SIC" };

const visibilityLabels: Record<string, string> = {
  PROFILE_NOT_APPROVED: "Perfil pendiente de revisión",
  PROFILE_PAUSED: "Perfil pausado",
  NO_ACTIVE_SUBSCRIPTION: "Suscripción pendiente",
  SERVICE_PAUSED: "Servicio pausado o pendiente",
  DOCUMENT_PENDING: "Documentación pendiente",
  DOCUMENT_EXPIRED: "Documentación vencida",
  NO_SERVICE_AREA: "Falta configurar cobertura",
  VISIBLE: "Visible",
};

export default async function ProviderDashboardPage({ searchParams }: { searchParams: Promise<{ status?: string; error?: string }> }) {
  const context = await providerPageContext({ requireProfile: true });
  let offers: ProviderOffer[] = [];
  if (context.input && context.profile && !context.apiUnavailable) {
    try { offers = await getProviderOffers(context.input); } catch { /* surfaced through the safe empty state */ }
  }
  const params = await searchParams;
  const activeOffers = offers.filter((offer) => offer.status === "ACTIVE").length;
  const visibleOffers = offers.filter((offer) => offer.visible).length;
  const profile = context.profile;

  return (
    <ProviderShell active="panel" displayName={profile?.display_name}>
      <div className="provider-page-heading"><div><p className="eyebrow">RESUMEN DE TU ACTIVIDAD</p><h1>{profile ? `Hola, ${profile.display_name}` : "Panel del prestador"}</h1><p>Configurá una oferta clara sin publicar datos incompletos.</p></div>{profile && <form action={toggleProviderProfile}><input type="hidden" name="paused" value={String(!profile.is_paused)} /><button className={profile.is_paused ? "primary" : "secondary"}>{profile.is_paused ? "Reanudar perfil" : "Pausar perfil"}</button></form>}</div>
      {!context.configured && <div className="preview-notice provider-page-notice">Vista previa protegida. Los datos reales aparecen con una sesión PROVIDER.</div>}
      {context.apiUnavailable && <div className="form-error provider-page-notice">No se pudo conectar con la API o PostgreSQL.</div>}
      {params.status && <div className="form-success provider-page-notice">El perfil se actualizó correctamente.</div>}
      {params.error && <div className="form-error provider-page-notice">No pudimos aplicar el cambio.</div>}

      <section className="provider-stat-grid">
        <article><span>▣</span><div><small>Servicios configurados</small><b>{offers.length}</b><p>{activeOffers} activos</p></div></article>
        <article><span>◉</span><div><small>Servicios visibles</small><b>{visibleOffers}</b><p>Solo con todos los requisitos</p></div></article>
        <article><span>☆</span><div><small>Portfolio</small><b>{profile?.portfolio.length ?? 0}</b><p>Trabajos registrados</p></div></article>
        <article><span>✓</span><div><small>Perfil completo</small><b>{profile?.profile_completeness ?? 0}%</b><p>Datos privados guardados</p></div></article>
      </section>

      <section className="provider-dashboard-grid">
        <article className="provider-dashboard-card provider-offers-card"><div className="provider-card-title"><div><span>▤</span><h2>Estado de tus servicios</h2></div><Link href="/prestador/servicios">Administrar</Link></div>{offers.length ? <div className="provider-offer-list">{offers.slice(0, 5).map((offer) => <div key={offer.id}><span><b>{offer.headline}</b><small>{offer.pricing_type === "QUOTE" ? "A presupuestar" : `Precio ${offer.pricing_type.toLowerCase()}`}</small></span><span className={offer.visible ? "readiness-ready" : "readiness-pending"}>{visibilityLabels[offer.visibility_code] ?? offer.visibility_code}</span></div>)}</div> : <div className="provider-dashboard-empty"><span>＋</span><h3>Todavía no configuraste servicios</h3><p>Elegí aptitudes del catálogo y definí cada modalidad por separado.</p><Link className="primary" href={profile ? "/prestador/servicios" : "/onboarding/prestador"}>{profile ? "Agregar servicio" : "Crear perfil"}</Link></div>}</article>
        <article className="provider-dashboard-card provider-quick-card"><div className="provider-card-title"><div><span>⚡</span><h2>Acciones rápidas</h2></div></div><Link href="/prestador/perfil"><span>♙</span><div><b>Completar perfil y portfolio</b><small>Nombre, experiencia y trabajos</small></div><i>›</i></Link><Link href="/prestador/servicios"><span>▣</span><div><b>Configurar servicios</b><small>Modalidad, precio y cobertura</small></div><i>›</i></Link><Link href="/prestador/documentacion"><span>▤</span><div><b>Validar documentación</b><small>Matrículas, certificados y estados</small></div><i>›</i></Link><Link href="/prestador/servicios#disponibilidad"><span>◫</span><div><b>Gestionar disponibilidad</b><small>Días, horarios y turnos</small></div><i>›</i></Link></article>
      </section>

      <section className="provider-readiness"><div><span>☆</span><div><b>Visibilidad protegida por requisitos</b><p>En esta fase ningún perfil se publica antes de documentación aprobada y suscripción válida.</p></div></div><div className="provider-readiness-progress"><b>{profile?.profile_completeness ?? 0}%</b><span><i style={{ width: `${profile?.profile_completeness ?? 0}%` }}></i></span><Link href="/prestador/perfil">Completar perfil</Link></div></section>
    </ProviderShell>
  );
}
