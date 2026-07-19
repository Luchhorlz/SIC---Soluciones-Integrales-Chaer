import manifest from "@/data/taxonomy-manifest.json";
import { getCatalogServices, getProviderAvailabilityExceptions, getProviderOffers, getUserAddresses, type AvailabilityException, type CatalogService, type ProviderOffer, type UserAddress } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";
import { ProviderShell } from "@/components/provider-shell";

import { createAvailabilityException, removeAvailabilityException, saveAvailability, toggleOffer } from "../actions";
import { OfferForm } from "./offer-form";

export const metadata = { title: "Mis servicios profesionales | SIC" };

const modalityLabels: Record<string, string> = { AT_CLIENT_ADDRESS: "A domicilio", REMOTE: "Remoto", HYBRID: "Híbrido", AT_PROVIDER_LOCATION: "En establecimiento", PICKUP_DELIVERY: "Retiro y entrega" };
const readinessLabels: Record<string, string> = { PROFILE_NOT_APPROVED: "Perfil pendiente", PROFILE_PAUSED: "Perfil pausado", NO_ACTIVE_SUBSCRIPTION: "Suscripción pendiente", SERVICE_PAUSED: "Servicio pendiente o pausado", DOCUMENT_PENDING: "Documentación pendiente", NO_SERVICE_AREA: "Falta cobertura", VISIBLE: "Visible" };

export default async function ProviderServicesPage({ searchParams }: { searchParams: Promise<{ status?: string; error?: string }> }) {
  const context = await providerPageContext({ requireProfile: true });
  let catalog: CatalogService[] = [];
  let offers: ProviderOffer[] = [];
  let addresses: UserAddress[] = [];
  let exceptions: AvailabilityException[] = [];
  let dataUnavailable = context.apiUnavailable;
  if (context.input && context.profile && !context.apiUnavailable) {
    try {
      [catalog, offers, addresses, exceptions] = await Promise.all([getCatalogServices(), getProviderOffers(context.input), getUserAddresses(context.input), getProviderAvailabilityExceptions(context.input)]);
    } catch { dataUnavailable = true; }
  }
  const params = await searchParams;
  const enabled = Boolean(context.input && context.profile && !dataUnavailable);
  const catalogNames = new Map(catalog.map((service) => [service.id, service.name]));

  return (
    <ProviderShell active="services" displayName={context.profile?.display_name}>
      <div className="provider-page-heading"><div><p className="eyebrow">OFERTA PROFESIONAL</p><h1>Mis servicios</h1><p>Elegí varias aptitudes del catálogo y configurá cada una por separado.</p></div><span className="provider-completeness-badge">{offers.length} configurados</span></div>
      {!context.configured && <div className="preview-notice provider-page-notice">Vista previa protegida: el catálogo aprobado contiene {manifest.services.toLocaleString("es-AR")} servicios.</div>}
      {dataUnavailable && context.configured && <div className="form-error provider-page-notice">No pudimos cargar el catálogo, las direcciones o PostgreSQL.</div>}
      {params.status && <div className="form-success provider-page-notice">La configuración se guardó correctamente.</div>}
      {params.error && <div className="form-error provider-page-notice">No pudimos guardar. Revisá modalidad, precio, cobertura y permisos del catálogo.</div>}

      <section className="provider-services-layout">
        <OfferForm catalog={catalog} addresses={addresses} enabled={enabled} />
        <div className="provider-configured-services">
          <div className="provider-section-title"><div><p className="eyebrow">CONFIGURADOS</p><h2>Servicios de tu perfil</h2></div><span>{offers.length}</span></div>
          {offers.length ? offers.map((offer) => <OfferCard key={offer.id} offer={offer} catalogName={catalogNames.get(offer.service_id) ?? "Servicio del catálogo"} enabled={enabled} />) : <div className="provider-dashboard-card provider-dashboard-empty"><span>▣</span><h3>Tu oferta todavía está vacía</h3><p>El formulario permite elegir servicios reales sin inventar aptitudes.</p></div>}
        </div>
      </section>
      <section className="provider-dashboard-card provider-exceptions-panel">
        <div className="provider-card-title"><div><span>◫</span><h2>Días y horarios no disponibles</h2></div><small>Agenda general</small></div>
        <div className="provider-exceptions-grid">
          <form action={createAvailabilityException}><p>Bloqueá vacaciones, turnos personales u otros períodos sin disponibilidad.</p><label>Desde<input name="starts_at" type="datetime-local" required disabled={!enabled} /></label><label>Hasta<input name="ends_at" type="datetime-local" required disabled={!enabled} /></label><label>Motivo privado<input name="reason" maxLength={240} disabled={!enabled} /></label><button className="secondary" disabled={!enabled}>Bloquear período</button></form>
          <div>{exceptions.length ? exceptions.map((item) => <article key={item.id}><div><b>{formatExceptionDate(item.starts_at)} — {formatExceptionDate(item.ends_at)}</b><p>{item.reason || "Sin motivo indicado"}</p></div><form action={removeAvailabilityException}><input type="hidden" name="item_id" value={item.id} /><button disabled={!enabled} aria-label="Eliminar período bloqueado">×</button></form></article>) : <div className="provider-mini-empty"><span>✓</span><p>No hay períodos bloqueados.</p></div>}</div>
        </div>
      </section>
    </ProviderShell>
  );
}

function formatExceptionDate(value: string): string {
  return new Intl.DateTimeFormat("es-AR", { timeZone: "America/Argentina/Buenos_Aires", dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function OfferCard({ offer, catalogName, enabled }: { offer: ProviderOffer; catalogName: string; enabled: boolean }) {
  const paused = offer.status === "PAUSED";
  return (
    <article className="provider-dashboard-card provider-service-card">
      <div className="provider-service-heading"><div><small>{catalogName}</small><h3>{offer.headline}</h3><p>{offer.description}</p></div><span className={offer.visible ? "readiness-ready" : "readiness-pending"}>{readinessLabels[offer.visibility_code] ?? offer.visibility_code}</span></div>
      <div className="provider-service-details"><span><b>{offer.pricing_type === "QUOTE" ? "A presupuestar" : `${offer.price_currency} ${offer.price_amount ?? ""}`}</b><small>Precio</small></span><span><b>{offer.modalities.map((item) => modalityLabels[item] ?? item).join(" · ")}</b><small>Modalidad</small></span><span><b>{offer.area ? `${(offer.area.radius_meters / 1000).toLocaleString("es-AR")} km` : "No aplica"}</b><small>Cobertura</small></span></div>
      <div className="provider-service-actions"><form action={toggleOffer}><input type="hidden" name="item_id" value={offer.id} /><input type="hidden" name="paused" value={String(!paused)} /><button className="secondary" disabled={!enabled}>{paused ? "Reanudar" : "Pausar servicio"}</button></form></div>
      <details id="disponibilidad" className="provider-availability"><summary>Configurar disponibilidad semanal <span>›</span></summary><form action={saveAvailability}><input type="hidden" name="item_id" value={offer.id} /><fieldset><legend>Días disponibles</legend>{["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"].map((day, index) => <label key={day}><input type="checkbox" name="days" value={index} disabled={!enabled} />{day}</label>)}</fieldset><div><label>Desde<input name="start_time" type="time" defaultValue="09:00" required disabled={!enabled} /></label><label>Hasta<input name="end_time" type="time" defaultValue="18:00" required disabled={!enabled} /></label><label>Duración del turno<select name="slot_duration_minutes" defaultValue="60" disabled={!enabled}><option value="30">30 minutos</option><option value="60">1 hora</option><option value="90">1 hora 30</option><option value="120">2 horas</option></select></label></div><p>Al guardar se reemplaza la agenda semanal de este servicio.</p><button className="primary" disabled={!enabled}>Guardar disponibilidad</button></form></details>
    </article>
  );
}
