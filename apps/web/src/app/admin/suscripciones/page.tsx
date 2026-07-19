import Link from "next/link";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { getAdminSubscriptionPlans, type SubscriptionPlan } from "@/lib/internal-api";

import { saveSubscriptionPlan } from "./actions";

export const metadata = { title: "Administrar suscripciones | SIC" };

function money(value: string | number, currency: string) {
  return new Intl.NumberFormat("es-AR", { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(value));
}

export default async function AdminSubscriptionsPage({ searchParams }: { searchParams: Promise<{ status?: string; error?: string }> }) {
  const configured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET);
  const session = configured ? await auth() : null;
  if (configured && !session?.user) redirect("/ingresar");
  if (configured && !session?.user.roles.includes("ADMIN")) redirect("/cuenta");
  const isAdmin = Boolean(session?.user.roles.includes("ADMIN"));
  let plans: SubscriptionPlan[] = [];
  let apiUnavailable = false;
  if (session?.user && isAdmin) {
    try { plans = await getAdminSubscriptionPlans({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId }); } catch { apiUnavailable = true; }
  }
  const params = await searchParams;
  const current = plans.find((plan) => plan.is_active) ?? plans[0];
  const disabled = !isAdmin || apiUnavailable;

  return (
    <main className="admin-documents-page">
      <header className="admin-header"><Link className="brand" href="/"><span className="brand-mark">S<span>Í</span>C</span><span>Soluciones Integrales Chaer</span></Link><div><span>Administración</span><Link href="/admin/catalogo">Catálogo</Link><Link href="/admin/documentos">Documentos</Link><Link href="/admin/opiniones">Opiniones</Link><Link href="/cuenta">Volver a mi cuenta</Link></div></header>
      <section className="admin-document-content">
        <div className="admin-title"><div><p className="eyebrow">FASE 7 · CONFIGURACIÓN COMERCIAL</p><h1>Suscripción mensual</h1><p>Definí el único plan inicial sin publicar precios ni beneficios ficticios.</p></div><span className="admin-lock">▣ Solo ADMIN</span></div>
        {!configured && <div className="preview-notice admin-notice">Vista previa protegida. La edición requiere una sesión ADMIN y PostgreSQL.</div>}
        {apiUnavailable && <div className="form-error">No pudimos conectar con la API de suscripciones.</div>}
        {params.status && <div className="form-success">El plan quedó guardado y será usado por los nuevos checkouts.</div>}
        {params.error && <div className="form-error">No pudimos guardar el plan. Revisá nombre, precio, moneda y código.</div>}

        <section className="admin-subscription-layout">
          <form action={saveSubscriptionPlan} className="provider-dashboard-card admin-subscription-form">
            <div className="provider-card-title"><div><span>◇</span><h2>{current ? "Editar plan vigente" : "Configurar plan inicial"}</h2></div><small>Frecuencia mensual</small></div>
            {current && <input type="hidden" name="plan_id" value={current.id} />}
            <label>Nombre visible<input name="name" minLength={3} maxLength={120} placeholder="Nombre comercial del plan" defaultValue={current?.name ?? ""} required disabled={disabled} /></label>
            {!current && <label>Código interno<input name="code" pattern="[A-Za-z][A-Za-z0-9_]{2,79}" defaultValue="SIC_MENSUAL" required disabled={disabled} /></label>}
            <div><label>Precio mensual<input name="price" type="number" min="0.01" step="0.01" placeholder="0,00" defaultValue={current?.price ?? ""} required disabled={disabled} /></label><label>Moneda<input name="currency" pattern="[A-Za-z]{3}" defaultValue={current?.currency ?? "ARS"} required disabled={disabled} /></label></div>
            <label>Beneficios, uno por línea<textarea name="features" rows={6} maxLength={3200} placeholder="Escribí únicamente beneficios aprobados" defaultValue={current?.features.join("\n") ?? ""} disabled={disabled}></textarea></label>
            <label className="admin-subscription-toggle"><input type="checkbox" name="is_active" defaultChecked={current?.is_active ?? true} disabled={disabled} /> Plan activo para nuevos checkouts</label>
            <button className="primary" disabled={disabled}>Guardar configuración</button>
            <p>Modificar este importe afecta nuevos checkouts. Las suscripciones ya autorizadas deben administrarse mediante el flujo correspondiente de Mercado Pago.</p>
          </form>

          <div className="admin-subscription-summary">
            <article className="provider-dashboard-card subscription-admin-preview"><div className="provider-card-title"><div><span>◉</span><h2>Vista operativa</h2></div><small>{plans.length} plan{plans.length === 1 ? "" : "es"}</small></div>{current ? <div><small>{current.code}</small><h3>{current.name}</h3><b>{money(current.price, current.currency)} <span>/ mes</span></b><p className={current.is_active ? "readiness-ready" : "readiness-pending"}>{current.is_active ? "Disponible" : "Inactivo"}</p><ul>{current.features.map((feature) => <li key={feature}>✓ {feature}</li>)}</ul></div> : <div className="provider-dashboard-empty"><span>◇</span><h3>Sin plan configurado</h3><p>El checkout del prestador permanece bloqueado hasta guardar un precio real.</p></div>}</article>
            <article className="provider-dashboard-card subscription-admin-security"><div className="provider-card-title"><div><span>▣</span><h2>Controles activos</h2></div></div><ul><li>Checkout alojado por Mercado Pago.</li><li>Firma HMAC y tolerancia temporal.</li><li>Evento persistido antes de procesar.</li><li>Identificador externo único.</li><li>Consulta del recurso antes de activar.</li></ul></article>
          </div>
        </section>
      </section>
    </main>
  );
}
