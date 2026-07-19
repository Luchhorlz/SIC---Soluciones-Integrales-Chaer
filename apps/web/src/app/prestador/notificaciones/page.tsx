import { NotificationList } from "@/components/notification-list";
import { ProviderShell } from "@/components/provider-shell";
import { getNotifications, type NotificationPage } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";

export const dynamic = "force-dynamic";
export const metadata = { title: "Notificaciones del prestador | SIC" };
const empty: NotificationPage = { notifications: [], unread_count: 0 };

export default async function ProviderNotificationsPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const context = await providerPageContext({ requireProfile: true }); let page = empty; let unavailable = context.apiUnavailable;
  if (context.input && context.profile && !unavailable) { try { page = await getNotifications(context.input); } catch { unavailable = true; } }
  const query = await searchParams;
  return <ProviderShell active="notifications" displayName={context.profile?.display_name}><div className="provider-page-heading"><div><p className="eyebrow">ACTIVIDAD PRIVADA</p><h1>Notificaciones</h1><p>Solicitudes, presupuestos, turnos y opiniones en un solo historial.</p></div><span className="provider-completeness-badge">{page.unread_count} nuevas</span></div>{!context.configured && <div className="preview-notice provider-page-notice">Vista previa: las notificaciones reales requieren autenticación y PostgreSQL.</div>}{(unavailable || query.error) && context.configured && <div className="form-error provider-page-notice">No pudimos actualizar las notificaciones.</div>}<div className="provider-message-wrapper"><NotificationList page={page} returnPath="/prestador/notificaciones" enabled={Boolean(context.input && !unavailable)} /></div></ProviderShell>;
}
