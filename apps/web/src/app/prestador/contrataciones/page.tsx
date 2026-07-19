import Link from "next/link";

import { ProviderShell } from "@/components/provider-shell";
import { getProviderBookings, type ServiceBooking } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";

import { updateProviderBooking } from "../engagement-actions";

export const dynamic = "force-dynamic";
export const metadata = { title: "Contrataciones del prestador | SIC" };
const labels: Record<string, string> = { PENDING_PROVIDER: "Pendiente de tu confirmación", CONFIRMED: "Confirmada", IN_PROGRESS: "En curso", COMPLETED: "Completada", CANCELLED_BY_CLIENT: "Cancelada por cliente", CANCELLED_BY_PROVIDER: "Cancelada por vos", NO_SHOW: "Ausencia", DISPUTED: "Reportada" };
function formatDate(value: string) { return new Intl.DateTimeFormat("es-AR", { timeZone: "America/Argentina/Buenos_Aires", dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }

export default async function ProviderBookingsPage({ searchParams }: { searchParams: Promise<{ status?: string; error?: string }> }) {
  const context = await providerPageContext({ requireProfile: true });
  let bookings: ServiceBooking[] = []; let unavailable = context.apiUnavailable;
  if (context.input && context.profile && !unavailable) { try { bookings = await getProviderBookings(context.input); } catch { unavailable = true; } }
  const query = await searchParams; const enabled = Boolean(context.input && context.profile && !unavailable);
  return <ProviderShell active="bookings" displayName={context.profile?.display_name}>
    <div className="provider-page-heading"><div><p className="eyebrow">AGENDA OPERATIVA</p><h1>Contrataciones</h1><p>Iniciá y completá únicamente turnos confirmados. Cada cambio queda validado por estado.</p></div><span className="provider-completeness-badge">{bookings.filter((item) => item.status === "CONFIRMED").length} próximas</span></div>
    {!context.configured && <div className="preview-notice provider-page-notice">Vista previa: los turnos reales requieren autenticación y PostgreSQL.</div>}{unavailable && context.configured && <div className="form-error provider-page-notice">No pudimos conectar la agenda privada.</div>}{query.status && <div className="form-success provider-page-notice">La contratación se actualizó correctamente.</div>}{query.error && <div className="form-error provider-page-notice">La acción no corresponde al estado actual del turno.</div>}
    <section className="provider-engagement-list">{bookings.length ? bookings.map((booking) => <ProviderBookingCard key={booking.id} booking={booking} enabled={enabled} />) : <div className="provider-dashboard-card engagement-empty"><span>▤</span><h3>No hay turnos confirmados</h3><p>Al aceptar una solicitud directa o cuando un cliente acepte tu presupuesto, aparecerá acá.</p></div>}</section>
  </ProviderShell>;
}

function ProviderBookingCard({ booking, enabled }: { booking: ServiceBooking; enabled: boolean }) {
  return <article className="provider-dashboard-card engagement-card"><header><div><small>{booking.service_name}</small><h2>{booking.offer_headline}</h2><p>Cliente: {booking.client_name}</p></div><span data-state={booking.status}>{labels[booking.status] ?? booking.status}</span></header>
    <div className="booking-facts"><span><small>Inicio</small><b>{formatDate(booking.starts_at)}</b></span><span><small>Fin</small><b>{formatDate(booking.ends_at)}</b></span><span><small>Importe</small><b>{booking.agreed_price ? `${booking.currency} ${booking.agreed_price}` : "A convenir"}</b></span></div>
    {booking.address && <div className="private-address"><b>⌖ Dirección compartida para este turno</b><span>{booking.address.formatted_address}{booking.address.unit ? ` · ${booking.address.unit}` : ""}</span></div>}
    <div className="engagement-actions">{booking.status === "PENDING_PROVIDER" && <><Action booking={booking} action="confirm" label="Confirmar horario" primary enabled={enabled} /><Action booking={booking} action="cancel" label="Rechazar horario" enabled={enabled} /></>}{booking.status === "CONFIRMED" && <><Action booking={booking} action="start" label="Iniciar servicio" primary enabled={enabled} /><Action booking={booking} action="cancel" label="Cancelar" enabled={enabled} /><Action booking={booking} action="no-show" label="Registrar ausencia" enabled={enabled} /></>}{booking.status === "IN_PROGRESS" && <Action booking={booking} action="complete" label="Marcar como completado" primary enabled={enabled} />}</div>
    <div className="engagement-actions"><Link className="secondary" href={`/prestador/mensajes?request=${booking.request_id}`}>Abrir mensajes</Link></div>
    {booking.client_confirmed_at && <p className="confirmed-copy">✓ El cliente confirmó la finalización.</p>}{booking.dispute_reason && <p className="dispute-copy">Reporte del cliente: {booking.dispute_reason}</p>}
  </article>;
}
function Action({ booking, action, label, primary = false, enabled }: { booking: ServiceBooking; action: string; label: string; primary?: boolean; enabled: boolean }) { return <form action={updateProviderBooking}><input type="hidden" name="booking_id" value={booking.id} /><button className={primary ? "primary" : "secondary"} name="action" value={action} disabled={!enabled}>{label}</button></form>; }
