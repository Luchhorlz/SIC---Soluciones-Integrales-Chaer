import Link from "next/link";

import { auth } from "@/auth";
import { getClientBookings, getClientServiceRequests, type ServiceBooking, type ServiceRequest } from "@/lib/internal-api";

import { cancelServiceRequest, decideQuote, updateClientBooking } from "./actions";

export const dynamic = "force-dynamic";
export const metadata = { title: "Mis contrataciones | SIC" };

const requestStatus: Record<string, string> = { REQUESTED: "Enviada", VIEWED: "Vista por el prestador", QUOTED: "Presupuestada", DECLINED: "Rechazada", CANCELLED: "Cancelada", EXPIRED: "Vencida", CONVERTED_TO_BOOKING: "Turno confirmado" };
const bookingStatus: Record<string, string> = { PENDING_PROVIDER: "Esperando confirmación", CONFIRMED: "Confirmada", IN_PROGRESS: "En curso", COMPLETED: "Completada", CANCELLED_BY_CLIENT: "Cancelada por vos", CANCELLED_BY_PROVIDER: "Cancelada por el prestador", NO_SHOW: "Ausencia registrada", DISPUTED: "Reportada" };
const openRequests = new Set(["REQUESTED", "VIEWED", "QUOTED"]);

function formatDate(value: string | null) {
  if (!value) return "Sin preferencia";
  return new Intl.DateTimeFormat("es-AR", { timeZone: "America/Argentina/Buenos_Aires", dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
function money(value: string | null, currency: string) {
  return value === null ? "A convenir" : new Intl.NumberFormat("es-AR", { style: "currency", currency }).format(Number(value));
}

export default async function ClientEngagementsPage({ searchParams }: { searchParams: Promise<{ status?: string; error?: string; warning?: string }> }) {
  const configured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET);
  const session = configured ? await auth() : null;
  let requests: ServiceRequest[] = []; let bookings: ServiceBooking[] = []; let unavailable = false;
  if (session?.user?.roles.includes("CLIENT")) {
    const input = { userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId };
    try { [requests, bookings] = await Promise.all([getClientServiceRequests(input), getClientBookings(input)]); } catch { unavailable = true; }
  }
  const query = await searchParams;
  const enabled = Boolean(session?.user?.roles.includes("CLIENT") && !unavailable);
  return <>
    <div className="account-top"><div><p className="eyebrow">SEGUIMIENTO PRIVADO</p><h1>Mis contrataciones</h1><p>Solicitudes, presupuestos y turnos confirmados en un solo lugar.</p></div><Link className="primary small" href="/buscar">Buscar prestadores</Link></div>
    {!configured && <div className="preview-notice account-preview">Vista previa activa. El circuito real aparecerá al configurar autenticación y PostgreSQL.</div>}
    {unavailable && <div className="form-error account-preview">La API privada o PostgreSQL no están disponibles.</div>}
    {query.status && <div className="form-success account-preview">La contratación se actualizó correctamente.</div>}
    {query.warning === "attachments" && <div className="preview-notice account-preview">La solicitud fue enviada, pero uno o más adjuntos no superaron la validación o el análisis. No se compartieron esos archivos.</div>}
    {query.error && <div className="form-error account-preview">No pudimos completar la acción. Revisá el estado y los horarios.</div>}

    <section className="engagement-section"><div className="engagement-heading"><div><p className="eyebrow">TURNOS</p><h2>Contrataciones confirmadas</h2></div><span>{bookings.length}</span></div>
      <div className="engagement-grid">{bookings.length ? bookings.map((booking) => <ClientBookingCard key={booking.id} booking={booking} enabled={enabled} />) : <div className="engagement-empty"><span>▣</span><h3>No hay turnos confirmados</h3><p>Cuando aceptes un presupuesto o el prestador confirme una oferta directa, aparecerá acá.</p></div>}</div>
    </section>

    <section className="engagement-section"><div className="engagement-heading"><div><p className="eyebrow">SOLICITUDES</p><h2>Conversaciones previas</h2></div><span>{requests.length}</span></div>
      <div className="engagement-grid">{requests.length ? requests.map((request) => <ClientRequestCard key={request.id} request={request} enabled={enabled} />) : <div className="engagement-empty"><span>◫</span><h3>Todavía no enviaste solicitudes</h3><p>Entrá al perfil de un prestador y elegí una de sus ofertas visibles.</p><Link className="secondary" href="/buscar">Explorar prestadores</Link></div>}</div>
    </section>
  </>;
}

function ClientBookingCard({ booking, enabled }: { booking: ServiceBooking; enabled: boolean }) {
  return <article className="engagement-card"><header><div><small>{booking.service_name}</small><h3>{booking.offer_headline}</h3><p>con {booking.provider_name}</p></div><span data-state={booking.status}>{bookingStatus[booking.status] ?? booking.status}</span></header>
    <div className="booking-facts"><span><small>Fecha</small><b>{formatDate(booking.starts_at)}</b></span><span><small>Importe acordado</small><b>{money(booking.agreed_price, booking.currency)}</b></span><span><small>Modalidad</small><b>{booking.modality}</b></span></div>
    {booking.address && <div className="private-address"><b>⌖ Dirección privada del turno</b><span>{booking.address.formatted_address}{booking.address.unit ? ` · ${booking.address.unit}` : ""}</span></div>}
    {(booking.status === "PENDING_PROVIDER" || booking.status === "CONFIRMED") && <form action={updateClientBooking}><input type="hidden" name="booking_id" value={booking.id} /><input type="hidden" name="action" value="cancel" /><button className="secondary" disabled={!enabled}>Cancelar turno</button></form>}
    {booking.status === "COMPLETED" && !booking.client_confirmed_at && <div className="engagement-actions"><form action={updateClientBooking}><input type="hidden" name="booking_id" value={booking.id} /><input type="hidden" name="action" value="confirm" /><button className="primary" disabled={!enabled}>Confirmar finalización</button></form><form className="dispute-form" action={updateClientBooking}><input type="hidden" name="booking_id" value={booking.id} /><input type="hidden" name="action" value="dispute" /><input name="reason" minLength={10} maxLength={500} required placeholder="Explicá qué ocurrió" disabled={!enabled} /><button className="secondary" disabled={!enabled}>Reportar problema</button></form></div>}
    {booking.client_confirmed_at && <p className="confirmed-copy">✓ Finalización confirmada por vos.</p>}{booking.dispute_reason && <p className="dispute-copy">Reporte: {booking.dispute_reason}</p>}
  </article>;
}

function ClientRequestCard({ request, enabled }: { request: ServiceRequest; enabled: boolean }) {
  const activeQuote = request.quotes.find((quote) => quote.status === "SENT");
  return <article className="engagement-card"><header><div><small>{request.service_name}</small><h3>{request.title}</h3><p>para {request.provider_name}</p></div><span data-state={request.status}>{requestStatus[request.status] ?? request.status}</span></header>
    <p className="engagement-description">{request.description}</p><div className="request-meta"><span>Preferencia: <b>{formatDate(request.preferred_start_at)}</b></span><span>Modalidad: <b>{request.selected_modality}</b></span>{request.client_address_label && <span>Dirección privada: <b>{request.client_address_label}</b></span>}</div>
    {request.attachments.length > 0 && <div className="attachment-list"><b>Adjuntos privados</b>{request.attachments.map((item) => <span key={item.id}>▤ {item.filename}</span>)}</div>}
    {activeQuote && <div className="quote-box"><div><small>PRESUPUESTO DEL PRESTADOR</small><b>{money(activeQuote.amount, activeQuote.currency)}</b><p>{activeQuote.description}</p><span>Válido hasta {formatDate(activeQuote.valid_until)}</span></div><form action={decideQuote}><input type="hidden" name="request_id" value={request.id} /><input type="hidden" name="quote_id" value={activeQuote.id} /><div><label>Inicio<input name="starts_at" type="datetime-local" required disabled={!enabled} /></label><label>Fin<input name="ends_at" type="datetime-local" required disabled={!enabled} /></label></div><button className="primary" name="decision" value="accept" disabled={!enabled}>Aceptar y reservar</button><button className="secondary" name="decision" value="reject" formNoValidate disabled={!enabled}>Rechazar</button></form></div>}
    {openRequests.has(request.status) && !activeQuote && <form action={cancelServiceRequest}><input type="hidden" name="request_id" value={request.id} /><button className="secondary" disabled={!enabled}>Cancelar solicitud</button></form>}
  </article>;
}
