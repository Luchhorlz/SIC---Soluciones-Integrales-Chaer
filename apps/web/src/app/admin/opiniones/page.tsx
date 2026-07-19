import Link from "next/link";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { isApplicationAuthConfigured } from "@/lib/auth-config";
import { getAdminReviews, type ServiceReview } from "@/lib/internal-api";

import { moderateReview } from "./actions";

export const dynamic = "force-dynamic";
export const metadata = { title: "Moderación de opiniones | SIC" };

const labels: Record<string, string> = { PENDING: "Pendiente", PUBLISHED: "Publicada", REJECTED: "Rechazada", HIDDEN: "Oculta" };

export default async function AdminReviewsPage({ searchParams }: { searchParams: Promise<{ status?: string; error?: string }> }) {
  const configured = isApplicationAuthConfigured();
  const session = configured ? await auth() : null;
  if (configured && !session?.user) redirect("/ingresar");
  if (configured && !session?.user.roles.includes("ADMIN")) redirect("/cuenta");
  const isAdmin = Boolean(session?.user.roles.includes("ADMIN"));
  let reviews: ServiceReview[] = [];
  let unavailable = false;
  if (session?.user && isAdmin) {
    try { reviews = await getAdminReviews({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId }); } catch { unavailable = true; }
  }
  const query = await searchParams;
  const pending = reviews.filter((item) => item.status === "PENDING");
  const history = reviews.filter((item) => item.status !== "PENDING");
  const enabled = isAdmin && !unavailable;

  return <main className="admin-reviews-page"><header className="admin-header"><Link className="brand" href="/"><span className="brand-mark">S<span>Í</span>C</span><span>Soluciones Integrales Chaer</span></Link><div><span>Administración</span><Link href="/admin/documentos">Documentos</Link><Link href="/admin/catalogo">Catálogo</Link><Link href="/admin/suscripciones">Suscripciones</Link><Link href="/cuenta">Mi cuenta</Link></div></header><section className="admin-review-content">
    <div className="admin-title"><div><p className="eyebrow">REPUTACIÓN · CONTROL HUMANO</p><h1>Moderación de opiniones</h1><p>Publicá únicamente reseñas verificadas y apropiadas. Cada cambio conserva su historial en la base.</p></div><span className="admin-lock">▣ Solo ADMIN</span></div>
    {!configured && <div className="preview-notice admin-notice">Vista previa protegida. La cola real requiere una sesión administrativa y PostgreSQL.</div>}
    {unavailable && <div className="form-error">No pudimos conectar con la cola de opiniones.</div>}{query.status && <div className="form-success">La decisión quedó registrada y el promedio fue recalculado.</div>}{query.error && <div className="form-error">No pudimos aplicar la decisión. Repetí el motivo si rechazás u ocultás.</div>}
    <section className="admin-review-stats"><article><b>{pending.length}</b><span>Pendientes</span></article><article><b>{reviews.filter((item) => item.status === "PUBLISHED").length}</b><span>Publicadas</span></article><article><b>{reviews.filter((item) => ["REJECTED", "HIDDEN"].includes(item.status)).length}</b><span>Restringidas</span></article></section>
    <section className="admin-opinion-queue"><div className="provider-section-title"><div><p className="eyebrow">COLA DE TRABAJO</p><h2>Opiniones pendientes</h2></div><span>{pending.length}</span></div>{pending.length ? pending.map((item) => <AdminReviewCard key={item.id} review={item} enabled={enabled} />) : <div className="provider-dashboard-card engagement-empty"><span>✓</span><h3>No hay opiniones pendientes</h3><p>Las nuevas reseñas verificadas aparecerán acá antes de ser públicas.</p></div>}</section>
    {history.length > 0 && <section className="admin-opinion-queue"><div className="provider-section-title"><div><p className="eyebrow">HISTORIAL</p><h2>Decisiones recientes</h2></div><span>{history.length}</span></div>{history.map((item) => <AdminReviewCard key={item.id} review={item} enabled={enabled} />)}</section>}
  </section></main>;
}

function AdminReviewCard({ review, enabled }: { review: ServiceReview; enabled: boolean }) {
  return <article className="provider-dashboard-card admin-opinion-card"><header><div><small>{review.service_name}</small><h3>{review.client_name} → {review.provider_name}</h3><p>{new Intl.DateTimeFormat("es-AR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(review.created_at))}</p></div><b data-status={review.status}>{labels[review.status] ?? review.status}</b></header><p className="review-stars">{"★".repeat(review.rating)}{"☆".repeat(5 - review.rating)}</p><blockquote>{review.comment}</blockquote>{review.moderation_reason && <p className="review-moderation-note">Motivo anterior: {review.moderation_reason}</p>}<form action={moderateReview}><input type="hidden" name="review_id" value={review.id} /><label>Motivo obligatorio para rechazar u ocultar<input name="reason" minLength={5} maxLength={500} disabled={!enabled} /></label><div>{review.status !== "PUBLISHED" && <button className="primary" name="action" value="publish" formNoValidate disabled={!enabled}>Publicar</button>}{review.status !== "REJECTED" && <button className="secondary" name="action" value="reject" disabled={!enabled}>Rechazar</button>}{review.status !== "HIDDEN" && <button className="secondary danger" name="action" value="hide" disabled={!enabled}>Ocultar</button>}</div></form></article>;
}
