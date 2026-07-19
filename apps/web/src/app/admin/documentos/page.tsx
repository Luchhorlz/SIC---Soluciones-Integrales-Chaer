import Link from "next/link";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { getAdminDocumentRequirements, getAdminDocuments, getCatalogServices, type AdminDocument, type CatalogService, type DocumentRequirement } from "@/lib/internal-api";

import { applyReviewAction, saveRequirement } from "./actions";

export const metadata = { title: "Revisión documental | SIC" };

const statusLabels: Record<string, string> = {
  SCANNING: "Esperando antivirus",
  PENDING: "Pendiente",
  IN_REVIEW: "En revisión",
  OBSERVED: "Observado",
  APPROVED: "Aprobado",
  REJECTED: "Rechazado",
  EXPIRED: "Vencido",
  SUSPENDED: "Suspendido",
};

export default async function AdminDocumentsPage({ searchParams }: { searchParams: Promise<{ status?: string; error?: string }> }) {
  const configured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET);
  const session = configured ? await auth() : null;
  if (configured && !session?.user) redirect("/ingresar");
  const roles = session?.user?.roles ?? [];
  const isAdmin = roles.includes("ADMIN");
  const canReview = isAdmin || roles.includes("DOCUMENT_REVIEWER");
  if (configured && !canReview) redirect("/cuenta");

  let catalog: CatalogService[] = [];
  let requirements: DocumentRequirement[] = [];
  let documents: AdminDocument[] = [];
  let apiUnavailable = false;
  if (session?.user && canReview) {
    const input = { userId: session.user.id, roles, sessionId: session.internalSessionId };
    try { [catalog, requirements, documents] = await Promise.all([getCatalogServices(), getAdminDocumentRequirements(input), getAdminDocuments(input)]); }
    catch { apiUnavailable = true; }
  }
  const params = await searchParams;
  const pending = documents.filter((item) => ["PENDING", "IN_REVIEW", "SCANNING"].includes(item.status)).length;
  const approved = documents.filter((item) => item.status === "APPROVED").length;
  const attention = documents.filter((item) => ["OBSERVED", "REJECTED", "EXPIRED", "SUSPENDED"].includes(item.status)).length;
  const enabled = canReview && !apiUnavailable;

  return (
    <main className="admin-documents-page">
      <header className="admin-header"><Link className="brand" href="/"><span className="brand-mark">S<span>Í</span>C</span><span>Soluciones Integrales Chaer</span></Link><div><span>Administración</span><Link href="/admin/catalogo">Catálogo</Link><Link href="/cuenta">Volver a mi cuenta</Link></div></header>
      <section className="admin-document-content">
        <div className="admin-title"><div><p className="eyebrow">FASE 6 · CONTROL PRIVADO</p><h1>Revisión documental</h1><p>Configurá requisitos por servicio y registrá cada decisión sin sobrescribir el historial.</p></div><span className="admin-lock">▣ ADMIN · DOCUMENT_REVIEWER</span></div>
        {!configured && <div className="preview-notice admin-notice">Vista previa protegida. La cola real requiere una sesión revisora y PostgreSQL.</div>}
        {apiUnavailable && <div className="form-error">No pudimos conectar con la API documental.</div>}
        {params.status && <div className="form-success">La operación quedó registrada en el historial.</div>}
        {params.error && <div className="form-error">No pudimos aplicar la operación. Revisá el estado y el motivo requerido.</div>}

        <div className="document-admin-stats"><article><b>{pending}</b><span>En proceso</span><small>Escaneo o revisión</small></article><article><b>{approved}</b><span>Aprobados</span><small>Actualmente vigentes</small></article><article><b>{attention}</b><span>Con observaciones</span><small>Requieren seguimiento</small></article><article><b>{requirements.filter((item) => item.is_required).length}</b><span>Requisitos activos</span><small>Sobre {requirements.length} configurados</small></article></div>

        <section className="admin-document-grid">
          <form action={saveRequirement} className="provider-dashboard-card admin-requirement-form">
            <div className="provider-card-title"><div><span>⚙</span><h2>Requisito por servicio</h2></div><small>Solo ADMIN</small></div>
            <label>Servicio<select name="service_id" required disabled={!isAdmin || apiUnavailable}><option value="">Seleccionar del catálogo</option>{catalog.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            <label>Código documental<input name="document_type" placeholder="MATRICULA_PROFESIONAL" pattern="[A-Za-z][A-Za-z0-9_]{2,79}" required disabled={!isAdmin || apiUnavailable} /></label>
            <label>Nombre visible<input name="label" placeholder="Matrícula profesional" minLength={3} maxLength={120} required disabled={!isAdmin || apiUnavailable} /></label>
            <label>Código de jurisdicción<input name="jurisdiction_type" defaultValue="NONE" pattern="[A-Za-z][A-Za-z0-9_]{1,39}" required disabled={!isAdmin || apiUnavailable} /></label>
            <label>Instrucciones<textarea name="instructions" rows={4} maxLength={2000} disabled={!isAdmin || apiUnavailable}></textarea></label>
            <div className="admin-requirement-checks"><label><input type="checkbox" name="is_required" defaultChecked disabled={!isAdmin || apiUnavailable} /> Requisito activo</label><label><input type="checkbox" name="requires_expiration" disabled={!isAdmin || apiUnavailable} /> Exige vencimiento</label></div>
            <button className="primary" disabled={!isAdmin || apiUnavailable}>Guardar requisito</button>
            <p>No se inventan requisitos legales: administración debe definirlos para cada servicio y jurisdicción aplicable.</p>
          </form>

          <div className="admin-requirement-list provider-dashboard-card">
            <div className="provider-card-title"><div><span>▤</span><h2>Reglas configuradas</h2></div><small>{requirements.length}</small></div>
            {requirements.length ? requirements.map((item) => <article key={item.id}><div><b>{item.label}</b><small>{item.service_name} · {item.document_type}</small></div><span className={item.is_required ? "readiness-ready" : "readiness-pending"}>{item.is_required ? "Activo" : "Inactivo"}</span></article>) : <div className="provider-mini-empty"><span>○</span><p>No hay requisitos cargados.</p></div>}
          </div>
        </section>

        <section className="admin-review-queue">
          <div className="provider-section-title"><div><p className="eyebrow">COLA DE TRABAJO</p><h2>Documentos recibidos</h2></div><span>{documents.length}</span></div>
          {documents.length ? documents.map((item) => <ReviewCard key={item.id} item={item} enabled={enabled} />) : <div className="provider-dashboard-card provider-dashboard-empty"><span>✓</span><h3>La cola está vacía</h3><p>Los documentos enviados por prestadores aparecerán aquí después del escaneo antivirus.</p></div>}
        </section>
      </section>
    </main>
  );
}

function ReviewCard({ item, enabled }: { item: AdminDocument; enabled: boolean }) {
  const canDownload = !["SCANNING", "REJECTED"].includes(item.status);
  return (
    <article className="provider-dashboard-card admin-review-card">
      <div className="admin-review-heading"><div><span>▤</span><div><small>{item.provider_display_name}</small><h3>{item.document_type.replaceAll("_", " ")}</h3><p>{item.holder_name}{item.document_number ? ` · Nº ${item.document_number}` : ""}</p></div></div><div><b className={item.status === "APPROVED" ? "readiness-ready" : "readiness-pending"}>{statusLabels[item.status] ?? item.status}</b>{canDownload && <Link href={`/api/admin/documents/${item.id}/download`}>Abrir archivo privado</Link>}</div></div>
      <div className="admin-document-metadata"><span><small>Emisor</small><b>{item.issuer || "No informado"}</b></span><span><small>Jurisdicción</small><b>{item.jurisdiction || "No informada"}</b></span><span><small>Vencimiento</small><b>{item.expires_at ? new Intl.DateTimeFormat("es-AR").format(new Date(`${item.expires_at}T12:00:00`)) : "No informado"}</b></span><span><small>Historial</small><b>{item.reviews.length} eventos</b></span></div>
      {item.rejection_reason && <p className="admin-review-observation">{item.rejection_reason}</p>}
      <form action={applyReviewAction} className="admin-review-form"><input type="hidden" name="document_id" value={item.id} />
        {item.status === "IN_REVIEW" && <><label>Motivo para observar, rechazar o suspender<textarea name="reason" rows={2} maxLength={2000} disabled={!enabled}></textarea></label><label>Nota interna<textarea name="internal_notes" rows={2} maxLength={4000} disabled={!enabled}></textarea></label></>}
        <div>
          {item.status === "SCANNING" && <button className="secondary" name="action" value="rescan" disabled={!enabled}>Reintentar antivirus</button>}
          {item.status === "PENDING" && <button className="primary" name="action" value="review" disabled={!enabled}>Tomar revisión</button>}
          {item.status === "IN_REVIEW" && <><button className="primary" name="action" value="approve" disabled={!enabled}>Aprobar</button><button className="secondary" name="action" value="observe" disabled={!enabled}>Observar</button><button className="secondary danger" name="action" value="reject" disabled={!enabled}>Rechazar</button></>}
          {item.status === "APPROVED" && <><input type="hidden" name="reason" value="Suspensión administrativa" /><button className="secondary danger" name="action" value="suspend" disabled={!enabled}>Suspender</button></>}
        </div>
      </form>
      <details className="admin-review-audit"><summary>Ver auditoría ({item.reviews.length})</summary>{item.reviews.map((review) => <p key={review.id}><b>{review.previous_status} → {review.new_status}</b><span>{review.reason || "Sin motivo adicional"}</span><small>{review.audit_reference}</small></p>)}</details>
    </article>
  );
}
