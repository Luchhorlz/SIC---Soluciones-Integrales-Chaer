import { auth } from "@/auth";
import { NotificationList } from "@/components/notification-list";
import { getNotifications, type NotificationPage } from "@/lib/internal-api";

export const dynamic = "force-dynamic";
export const metadata = { title: "Notificaciones | SIC" };
const empty: NotificationPage = { notifications: [], unread_count: 0 };

export default async function ClientNotificationsPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const configured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET);
  const session = configured ? await auth() : null; let page = empty; let unavailable = false;
  if (session?.user) { try { page = await getNotifications({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId }); } catch { unavailable = true; } }
  const query = await searchParams;
  return <><div className="account-top"><div><p className="eyebrow">ACTIVIDAD PRIVADA</p><h1>Notificaciones</h1><p>Avisos transaccionales sobre tu actividad en SIC.</p></div></div>{!configured && <div className="preview-notice account-preview">Vista previa: las notificaciones reales requieren autenticación y PostgreSQL.</div>}{(unavailable || query.error) && <div className="form-error account-preview">No pudimos actualizar las notificaciones.</div>}<NotificationList page={page} returnPath="/cuenta/notificaciones" enabled={Boolean(session?.user && !unavailable)} /></>;
}
