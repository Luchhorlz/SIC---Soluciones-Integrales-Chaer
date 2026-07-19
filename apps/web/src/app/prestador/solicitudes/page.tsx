import { ProviderShell } from "@/components/provider-shell";
import { getProviderServiceRequests, type ServiceRequest } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";

import { acceptDirectRequest, declineProviderRequest, markRequestViewed, quoteProviderRequest } from "../engagement-actions";

export const dynamic = "force-dynamic";
export const metadata = { title: "Solicitudes de clientes | SIC" };
const labels: Record<string, string> = { REQUESTED: "Nueva", VIEWED: "Vista", QUOTED: "Presupuestada", DECLINED: "Rechazada", CANCELLED: "Cancelada", CONVERTED_TO_BOOKING: "Convertida en turno" };
const actionable = new Set(["REQUESTED", "VIEWED", "QUOTED"]);
function formatDate(value: string | null) { return value ? new Intl.DateTimeFormat("es-AR", { timeZone: "America/Argentina/Buenos_Aires", dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Sin preferencia"; }

export default async function ProviderRequestsPage({ searchParams }: { searchParams: Promise<{ status?: string; error?: string }> }) {
  const context = await providerPageContext({ requireProfile: true });
  let requests: ServiceRequest[] = []; let unavailable = context.apiUnavailable;
  if (context.input && context.profile && !unavailable) { try { requests = await getProviderServiceRequests(context.input); } catch { unavailable = true; } }
  const query = await searchParams; const enabled = Boolean(context.input && context.profile && !unavailable);
  return <ProviderShell active="requests" displayName={context.profile?.display_name}>
    <div className="provider-page-heading"><div><p className="eyebrow">BANDEJA PRIVADA</p><h1>Solicitudes</h1><p>Revisá el pedido del cliente, presupuestá o confirmá una oferta con precio directo.</p></div><span className="provider-completeness-badge">{requests.filter((item) => item.status === "REQUESTED").length} nuevas</span></div>
    {!context.configured && <div className="preview-notice provider-page-notice">Vista previa: las solicitudes reales requieren autenticación y PostgreSQL.</div>}{unavailable && context.configured && <div className="form-error provider-page-notice">No pudimos conectar la bandeja privada.</div>}{query.status && <div className="form-success provider-page-notice">La solicitud se actualizó correctamente.</div>}{query.error && <div className="form-error provider-page-notice">La acción no es válida para el estado actual o el horario ya no está disponible.</div>}
    <section className="provider-engagement-list">{requests.length ? requests.map((request) => <ProviderRequestCard key={request.id} request={request} enabled={enabled} />) : <div className="provider-dashboard-card engagement-empty"><span>◫</span><h3>No hay solicitudes</h3><p>Las nuevas consultas privadas de clientes aparecerán en esta bandeja.</p></div>}</section>
  </ProviderShell>;
}

function ProviderRequestCard({ request, enabled }: { request: ServiceRequest; enabled: boolean }) {
  const canAct = actionable.has(request.status);
  return <article className="provider-dashboard-card engagement-card"><header><div><small>{request.service_name}</small><h2>{request.title}</h2><p>Cliente: {request.client_name}</p></div><span data-state={request.status}>{labels[request.status] ?? request.status}</span></header>
    <p className="engagement-description">{request.description}</p><div className="request-meta"><span>Preferencia: <b>{formatDate(request.preferred_start_at)}</b></span><span>Modalidad: <b>{request.selected_modality}</b></span>{request.client_address_label && <span>Zona privada: <b>{request.client_address_label}</b></span>}</div>
    {request.attachments.length > 0 && <div className="attachment-list"><b>Adjuntos validados</b>{request.attachments.map((item) => <span key={item.id}>▤ {item.filename}</span>)}</div>}
    {request.status === "REQUESTED" && <form action={markRequestViewed}><input type="hidden" name="request_id" value={request.id} /><button className="secondary" disabled={!enabled}>Marcar como vista</button></form>}
    {canAct && request.pricing_type !== "FIXED" && <form className="engagement-response-form" action={quoteProviderRequest}><input type="hidden" name="request_id" value={request.id} /><h3>Enviar presupuesto</h3><div><label>Importe ARS<input name="amount" type="number" min="1" step="0.01" required disabled={!enabled} /></label><label>Válido hasta<input name="valid_until" type="datetime-local" required disabled={!enabled} /></label></div><label>Alcance y condiciones<textarea name="description" minLength={10} maxLength={3000} required disabled={!enabled}></textarea></label><button className="primary" disabled={!enabled}>Enviar presupuesto</button></form>}
    {canAct && request.pricing_type === "FIXED" && <form className="engagement-response-form" action={acceptDirectRequest}><input type="hidden" name="request_id" value={request.id} /><h3>Confirmar por {request.price_currency} {request.configured_price}</h3><div><label>Inicio<input name="starts_at" type="datetime-local" required disabled={!enabled} /></label><label>Fin<input name="ends_at" type="datetime-local" required disabled={!enabled} /></label></div><button className="primary" disabled={!enabled}>Aceptar y crear turno</button></form>}
    {canAct && <form action={declineProviderRequest}><input type="hidden" name="request_id" value={request.id} /><button className="secondary" disabled={!enabled}>Rechazar solicitud</button></form>}
  </article>;
}
