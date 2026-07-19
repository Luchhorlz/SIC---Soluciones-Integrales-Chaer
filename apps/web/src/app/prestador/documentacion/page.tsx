import Link from "next/link";

import { ProviderShell } from "@/components/provider-shell";
import { getProviderDocuments, getProviderDocumentRequirements, type ProviderDocument, type ProviderRequirement } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";

export const metadata = { title: "Documentación profesional | SIC" };

const statusLabels: Record<string, string> = {
  SCANNING: "Escaneando",
  PENDING: "Pendiente",
  IN_REVIEW: "En revisión",
  OBSERVED: "Observado",
  APPROVED: "Aprobado",
  REJECTED: "Rechazado",
  EXPIRED: "Vencido",
  SUSPENDED: "Suspendido",
};

export default async function ProviderDocumentsPage({ searchParams }: { searchParams: Promise<{ status?: string; error?: string }> }) {
  const context = await providerPageContext({ requireProfile: true });
  let requirements: ProviderRequirement[] = [];
  let documents: ProviderDocument[] = [];
  let dataUnavailable = context.apiUnavailable;
  if (context.input && context.profile && !dataUnavailable) {
    try {
      [requirements, documents] = await Promise.all([getProviderDocumentRequirements(context.input), getProviderDocuments(context.input)]);
    } catch { dataUnavailable = true; }
  }
  const params = await searchParams;
  const enabled = Boolean(context.input && context.profile && !dataUnavailable && requirements.length);
  const uniqueRequirements = Array.from(new Map(requirements.map((item) => [item.document_type, item])).values());
  const approved = documents.filter((item) => item.status === "APPROVED").length;
  const pending = documents.filter((item) => ["SCANNING", "PENDING", "IN_REVIEW"].includes(item.status)).length;
  const attention = documents.filter((item) => ["OBSERVED", "REJECTED", "EXPIRED", "SUSPENDED"].includes(item.status)).length;

  return (
    <ProviderShell active="documents" displayName={context.profile?.display_name}>
      <div className="provider-page-heading"><div><p className="eyebrow">VALIDACIÓN PROFESIONAL</p><h1>Documentación</h1><p>Cargá matrículas o certificados solo cuando un servicio configurado los requiera.</p></div><span className="provider-completeness-badge">Archivos privados</span></div>
      {!context.configured && <div className="preview-notice provider-page-notice">Vista previa protegida. Las cargas se habilitan con sesión PROVIDER, MinIO y ClamAV.</div>}
      {dataUnavailable && context.configured && <div className="form-error provider-page-notice">No pudimos consultar la documentación privada.</div>}
      {params.status && <div className="form-success provider-page-notice">El documento fue recibido y quedó pendiente de revisión.</div>}
      {params.error && <div className="form-error provider-page-notice">No pudimos cargar el archivo. Revisá el requisito, formato, tamaño y antivirus.</div>}

      <section className="document-stat-grid">
        <article><span>▤</span><div><small>Requisitos</small><b>{requirements.length}</b><p>Según tus servicios</p></div></article>
        <article><span>◷</span><div><small>En proceso</small><b>{pending}</b><p>Escaneo o revisión</p></div></article>
        <article><span>✓</span><div><small>Aprobados</small><b>{approved}</b><p>Vigentes</p></div></article>
        <article><span>!</span><div><small>Requieren atención</small><b>{attention}</b><p>Observados o vencidos</p></div></article>
      </section>

      <section className="provider-documents-layout">
        <form className="provider-dashboard-card document-upload-card" action="/api/provider/documents" method="post" encType="multipart/form-data">
          <div className="provider-card-title"><div><span>↑</span><h2>Cargar documento</h2></div><small>PDF, PNG o JPEG · máximo 10 MB</small></div>
          <div className="document-form-grid">
            <label className="wide">Requisito<select name="document_type" required disabled={!enabled}><option value="">Seleccionar</option>{uniqueRequirements.map((item) => <option key={item.document_type} value={item.document_type}>{item.label}</option>)}</select></label>
            <label>Titular<input name="holder_name" minLength={2} maxLength={180} required disabled={!enabled} /></label>
            <label>Número<input name="document_number" maxLength={120} disabled={!enabled} /></label>
            <label>Emisor<input name="issuer" maxLength={180} disabled={!enabled} /></label>
            <label>Jurisdicción<input name="jurisdiction" maxLength={180} disabled={!enabled} /></label>
            <label>Fecha de emisión<input name="issued_at" type="date" disabled={!enabled} /></label>
            <label>Vencimiento<input name="expires_at" type="date" disabled={!enabled} /></label>
            <label className="wide document-file-field"><span>Archivo privado</span><input name="file" type="file" accept="application/pdf,image/png,image/jpeg" required disabled={!enabled} /><small>El nombre se reemplaza por un UUID y el archivo se escanea antes de revisarlo.</small></label>
          </div>
          <button className="primary" disabled={!enabled}>Enviar a validación</button>
          {!requirements.length && <p className="document-no-requirements">Tus servicios actuales no tienen requisitos documentales configurados. No necesitás subir archivos.</p>}
        </form>

        <div className="document-requirement-column">
          <div className="provider-section-title"><div><p className="eyebrow">POR SERVICIO</p><h2>Requisitos detectados</h2></div><span>{requirements.length}</span></div>
          {requirements.length ? requirements.map((item) => <RequirementCard key={item.id} item={item} />) : <div className="provider-dashboard-card provider-dashboard-empty"><span>✓</span><h3>Sin documentación pendiente</h3><p>Si administración configura un requisito para alguno de tus servicios, aparecerá en esta sección.</p></div>}
        </div>
      </section>

      <section className="provider-dashboard-card provider-document-history">
        <div className="provider-card-title"><div><span>◴</span><h2>Historial de envíos</h2></div><small>No se eliminan decisiones anteriores</small></div>
        {documents.length ? <div className="document-history-list">{documents.map((item) => <DocumentHistory key={item.id} item={item} />)}</div> : <div className="provider-mini-empty"><span>▤</span><p>Todavía no enviaste documentación.</p></div>}
      </section>
    </ProviderShell>
  );
}

function RequirementCard({ item }: { item: ProviderRequirement }) {
  const status = item.latest_document?.status;
  return (
    <article className="provider-dashboard-card document-requirement-card">
      <div><span className={item.satisfied ? "document-ok" : item.expired ? "document-alert" : "document-pending"}>{item.satisfied ? "✓" : item.expired ? "!" : "○"}</span><div><small>{item.service_name}</small><h3>{item.label}</h3></div></div>
      <p>{item.instructions || "Administración no agregó instrucciones adicionales."}</p>
      <div><span>{item.requires_expiration ? "Requiere vencimiento" : "Sin vencimiento obligatorio"}</span><b className={item.satisfied ? "readiness-ready" : "readiness-pending"}>{status ? statusLabels[status] ?? status : "Falta cargar"}</b></div>
    </article>
  );
}

function DocumentHistory({ item }: { item: ProviderDocument }) {
  const downloadable = !["SCANNING", "REJECTED"].includes(item.status);
  return (
    <article><div className="document-history-icon">▤</div><div><b>{item.document_type.replaceAll("_", " ")}</b><small>{item.filename} · {(item.byte_size / 1024).toLocaleString("es-AR", { maximumFractionDigits: 0 })} KB</small>{item.rejection_reason && <p>{item.rejection_reason}</p>}</div><div><span className={["APPROVED"].includes(item.status) ? "readiness-ready" : "readiness-pending"}>{statusLabels[item.status] ?? item.status}</span><small>{new Intl.DateTimeFormat("es-AR", { dateStyle: "short" }).format(new Date(item.submitted_at))}</small>{downloadable && <Link href={`/api/provider/documents/${item.id}/download`}>Descargar</Link>}</div></article>
  );
}
