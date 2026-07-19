import { ProviderShell } from "@/components/provider-shell";
import { getProviderReviews, type ServiceReview } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";

export const dynamic = "force-dynamic";
export const metadata = { title: "Opiniones recibidas | SIC" };

const labels: Record<string, string> = { PENDING: "En moderación", PUBLISHED: "Publicada", REJECTED: "Rechazada", HIDDEN: "Oculta" };

export default async function ProviderReviewsPage() {
  const context = await providerPageContext({ requireProfile: true });
  let reviews: ServiceReview[] = [];
  let unavailable = context.apiUnavailable;
  if (context.input && context.profile && !unavailable) {
    try { reviews = await getProviderReviews(context.input); } catch { unavailable = true; }
  }
  const published = reviews.filter((item) => item.status === "PUBLISHED");
  const average = published.length ? published.reduce((sum, item) => sum + item.rating, 0) / published.length : 0;

  return <ProviderShell active="reviews" displayName={context.profile?.display_name}>
    <div className="provider-page-heading"><div><p className="eyebrow">REPUTACIÓN VERIFICADA</p><h1>Opiniones</h1><p>Solo aparecen comentarios asociados a trabajos completados y confirmados por el cliente.</p></div><span className="provider-completeness-badge">{published.length ? `${average.toFixed(1)} ★` : "Sin promedio"}</span></div>
    {!context.configured && <div className="preview-notice provider-page-notice">Vista previa: las opiniones reales requieren autenticación y PostgreSQL.</div>}
    {unavailable && context.configured && <div className="form-error provider-page-notice">No pudimos cargar las opiniones privadas.</div>}
    <section className="provider-review-summary"><article><b>{published.length}</b><span>Publicadas</span><small>Computan en tu promedio</small></article><article><b>{reviews.filter((item) => item.status === "PENDING").length}</b><span>En moderación</span><small>Todavía no son públicas</small></article><article><b>{published.length ? average.toFixed(1) : "—"}</b><span>Promedio público</span><small>Solo reseñas aprobadas</small></article></section>
    <section className="provider-review-list">{reviews.length ? reviews.map((review) => <ProviderReviewCard key={review.id} review={review} />) : <div className="provider-dashboard-card engagement-empty"><span>☆</span><h3>Todavía no recibiste opiniones</h3><p>Después de completar un trabajo, el cliente podrá dejar una reseña verificada.</p></div>}</section>
  </ProviderShell>;
}

function ProviderReviewCard({ review }: { review: ServiceReview }) {
  return <article className="provider-dashboard-card provider-review-card"><header><div><small>{review.service_name}</small><h2>{review.client_name}</h2><p>{new Intl.DateTimeFormat("es-AR", { dateStyle: "medium" }).format(new Date(review.created_at))}</p></div><b data-status={review.status}>{labels[review.status] ?? review.status}</b></header><p className="review-stars" aria-label={`${review.rating} de 5 estrellas`}>{"★".repeat(review.rating)}{"☆".repeat(5 - review.rating)}</p><blockquote>{review.comment}</blockquote>{review.moderation_reason && <p className="review-moderation-note">Decisión de moderación: {review.moderation_reason}</p>}</article>;
}
