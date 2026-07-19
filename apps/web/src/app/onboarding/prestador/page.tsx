import Link from "next/link";
import { redirect } from "next/navigation";

import { getUserAddresses, type UserAddress } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";
import { saveProviderProfile } from "@/app/prestador/actions";

export const metadata = { title: "Activá tu perfil de prestador | SIC" };

export default async function ProviderOnboardingPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const context = await providerPageContext();
  if (context.configured && context.profile) redirect("/prestador/panel");
  let addresses: UserAddress[] = [];
  if (context.input && !context.apiUnavailable) {
    try { addresses = await getUserAddresses(context.input); } catch { /* The form remains usable without a base address. */ }
  }
  const params = await searchParams;
  const enabled = Boolean(context.input && !context.apiUnavailable);

  return (
    <main className="provider-onboarding">
      <header className="onboarding-header">
        <Link className="brand" href="/"><span className="brand-mark">S<span>Í</span>C</span><span>Soluciones Integrales Chaer</span></Link>
        <div className="onboarding-progress"><span>1</span><i></i><span className="active">2</span><i></i><span>3</span></div>
        <Link className="exit-link" href="/">Salir</Link>
      </header>
      <section className="provider-onboarding-layout">
        <div className="provider-onboarding-copy">
          <p className="eyebrow">PASO 2 DE 3 · PERFIL PRIVADO</p>
          <h1>Contanos sobre tu trabajo</h1>
          <p>Esta información prepara tu perfil. Todavía no será público hasta completar documentación, revisión y suscripción.</p>
          <ul><li><span>1</span>Creá tu identidad profesional.</li><li><span>2</span>Después elegí varios servicios.</li><li><span>3</span>Cada servicio tendrá su propia modalidad y cobertura.</li></ul>
        </div>
        <form action={saveProviderProfile} className="provider-form-card">
          <input type="hidden" name="mode" value="create" />
          <div><p className="eyebrow">DATOS PRINCIPALES</p><h2>Perfil del prestador</h2><p>Podrás editarlo cuando quieras.</p></div>
          {!context.configured && <div className="preview-notice">Vista previa: el guardado se habilita con Google, rol PROVIDER y PostgreSQL.</div>}
          {context.apiUnavailable && <div className="form-error">La API o PostgreSQL no están disponibles.</div>}
          {params.error && <div className="form-error">No pudimos crear el perfil. Revisá los campos y la dirección seleccionada.</div>}
          <div className="provider-form-grid">
            <label>Nombre visible<input name="display_name" minLength={2} maxLength={180} required disabled={!enabled} placeholder="Tu nombre o nombre profesional" /></label>
            <label>Nombre comercial <small>Opcional</small><input name="business_name" maxLength={180} disabled={!enabled} /></label>
            <label className="wide">Presentación profesional<textarea name="bio" rows={5} maxLength={3000} disabled={!enabled} placeholder="Experiencia, forma de trabajo y qué pueden esperar tus clientes"></textarea></label>
            <label>Años de experiencia<input name="experience_years" type="number" min="0" max="80" disabled={!enabled} /></label>
            <label>Dirección base validada<select name="base_address_id" disabled={!enabled}><option value="">Agregar más adelante</option>{addresses.map((address) => <option key={address.id} value={address.id}>{address.label} · {address.city}</option>)}</select></label>
          </div>
          {!addresses.length && <p className="provider-form-hint">Podés continuar sin dirección. Las modalidades presenciales la exigirán cuando configures cobertura.</p>}
          <div className="provider-form-actions"><Link className="secondary" href="/onboarding/rol">Volver</Link><button className="primary" disabled={!enabled}>Crear perfil y continuar</button></div>
        </form>
      </section>
    </main>
  );
}
