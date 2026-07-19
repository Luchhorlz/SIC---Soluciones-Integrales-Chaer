import { ProviderShell } from "@/components/provider-shell";
import { getProviderSubscription, type ProviderSubscriptionPage } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";

export const metadata = { title: "Suscripción mensual | SIC" };

const statusLabels: Record<string, string> = {
  PENDING: "Pendiente de completar",
  AUTHORIZED: "Autorizada",
  ACTIVE: "Activa",
  PAST_DUE: "Pago pendiente",
  PAUSED: "Pausada",
  CANCELLED: "Cancelada",
  EXPIRED: "Vencida",
  ERROR: "Requiere revisión",
};

function money(value: string | number, currency: string) {
  return new Intl.NumberFormat("es-AR", { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(value));
}

export default async function ProviderSubscriptionPageView({ searchParams }: { searchParams: Promise<{ checkout?: string; error?: string }> }) {
  const context = await providerPageContext({ requireProfile: true });
  let data: ProviderSubscriptionPage | null = null;
  let apiUnavailable = context.apiUnavailable;
  if (context.input && context.profile && !apiUnavailable) {
    try { data = await getProviderSubscription(context.input); } catch { apiUnavailable = true; }
  }
  const params = await searchParams;
  const plan = data?.plan;
  const subscription = data?.subscription;
  const active = subscription?.status === "ACTIVE" || subscription?.status === "AUTHORIZED";

  return (
    <ProviderShell active="subscription" displayName={context.profile?.display_name}>
      <div className="provider-page-heading"><div><p className="eyebrow">MEMBRESÍA PROFESIONAL</p><h1>Suscripción mensual</h1><p>Tu suscripción habilita la posibilidad de aparecer, pero no reemplaza la revisión del perfil ni la documentación.</p></div><span className={active ? "subscription-status active" : "subscription-status"}>{subscription ? statusLabels[subscription.status] ?? subscription.status : "Sin suscripción"}</span></div>
      {!context.configured && <div className="preview-notice provider-page-notice">Vista previa protegida. El checkout real requiere una sesión PROVIDER y credenciales sandbox.</div>}
      {apiUnavailable && context.configured && <div className="form-error provider-page-notice">No pudimos consultar el estado de la suscripción.</div>}
      {params.checkout && <div className="form-success provider-page-notice">Volviste de Mercado Pago. El estado se confirmará únicamente cuando llegue el evento verificado.</div>}
      {params.error && <div className="form-error provider-page-notice">No pudimos iniciar el checkout. Revisá que el plan y Mercado Pago sandbox estén configurados.</div>}

      <section className="subscription-layout">
        <article className="provider-dashboard-card subscription-plan-card">
          <div className="subscription-plan-heading"><span>◇</span><div><small>PLAN DISPONIBLE</small><h2>{plan?.name ?? "Plan mensual pendiente de definición"}</h2></div></div>
          {plan ? <><div className="subscription-price"><b>{money(plan.price, plan.currency)}</b><span>/ mes</span></div><ul>{plan.features.length ? plan.features.map((feature) => <li key={feature}>✓ {feature}</li>) : <li>✓ Habilita la visibilidad cuando todos los demás requisitos están aprobados.</li>}</ul></> : <p className="subscription-empty-copy">Administración todavía no definió nombre y precio. SIC no muestra importes ficticios.</p>}
          <p className="subscription-explanation">{data?.message ?? "El checkout permanecerá deshabilitado hasta completar la configuración comercial y técnica."}</p>
          <form action="/api/provider/subscription/checkout" method="post"><button className="primary" disabled={!data?.checkout_available}>Continuar en Mercado Pago</button></form>
          <small className="subscription-secure-note">El medio de pago se ingresa únicamente en Mercado Pago.</small>
        </article>

        <div className="subscription-side-column">
          <article className="provider-dashboard-card subscription-state-card"><div className="provider-card-title"><div><span>◉</span><h2>Estado actual</h2></div></div><div><span className={active ? "subscription-state-dot active" : "subscription-state-dot"}></span><div><b>{subscription ? statusLabels[subscription.status] ?? subscription.status : "Todavía no iniciada"}</b><p>{subscription?.current_period_end ? `Próxima revisión: ${new Intl.DateTimeFormat("es-AR", { dateStyle: "long" }).format(new Date(subscription.current_period_end))}` : "Se actualizará desde eventos verificados del proveedor de cobro."}</p></div></div></article>
          <article className="provider-dashboard-card subscription-rules-card"><div className="provider-card-title"><div><span>✓</span><h2>Qué controla SIC</h2></div></div><ul><li>Suscripción activa o autorizada.</li><li>Perfil aprobado y sin pausas.</li><li>Documentación requerida aprobada y vigente.</li><li>Servicio, modalidad y cobertura correctamente configurados.</li></ul><p>Si la suscripción vence, SIC oculta los servicios sin borrar información.</p></article>
        </div>
      </section>
    </ProviderShell>
  );
}
