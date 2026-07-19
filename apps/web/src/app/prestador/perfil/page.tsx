import { getUserAddresses, type UserAddress } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";
import { ProviderShell } from "@/components/provider-shell";

import { createPortfolioItem, removePortfolioItem, saveProviderProfile } from "../actions";

export const metadata = { title: "Mi perfil profesional | SIC" };

export default async function ProviderProfilePage({ searchParams }: { searchParams: Promise<{ status?: string; error?: string }> }) {
  const context = await providerPageContext({ requireProfile: true });
  const profile = context.profile;
  let addresses: UserAddress[] = [];
  if (context.input && !context.apiUnavailable) {
    try { addresses = await getUserAddresses(context.input); } catch { /* profile stays editable without an address */ }
  }
  const params = await searchParams;
  const enabled = Boolean(context.input && profile && !context.apiUnavailable);

  return (
    <ProviderShell active="profile" displayName={profile?.display_name}>
      <div className="provider-page-heading"><div><p className="eyebrow">IDENTIDAD PROFESIONAL</p><h1>Mi perfil y portfolio</h1><p>Los cambios permanecen privados hasta que SIC habilite la visibilidad.</p></div><span className="provider-completeness-badge">{profile?.profile_completeness ?? 0}% completo</span></div>
      {!context.configured && <div className="preview-notice provider-page-notice">Vista previa: los formularios están protegidos.</div>}
      {params.status && <div className="form-success provider-page-notice">Los cambios se guardaron correctamente.</div>}
      {params.error && <div className="form-error provider-page-notice">No pudimos guardar los cambios.</div>}

      <section className="provider-profile-grid">
        <form action={saveProviderProfile} className="provider-dashboard-card provider-profile-form">
          <input type="hidden" name="mode" value="update" />
          <div className="provider-card-title"><div><span>♙</span><h2>Datos del perfil</h2></div><small>Slug estable: /{profile?.slug ?? "prestador"}</small></div>
          <div className="provider-form-grid">
            <label>Nombre visible<input name="display_name" defaultValue={profile?.display_name ?? ""} required disabled={!enabled} /></label>
            <label>Nombre comercial<input name="business_name" defaultValue={profile?.business_name ?? ""} disabled={!enabled} /></label>
            <label className="wide">Presentación<textarea name="bio" rows={6} defaultValue={profile?.bio ?? ""} maxLength={3000} disabled={!enabled}></textarea></label>
            <label>Años de experiencia<input name="experience_years" type="number" min="0" max="80" defaultValue={profile?.experience_years ?? ""} disabled={!enabled} /></label>
            <label>Dirección base<select name="base_address_id" defaultValue={profile?.base_address_id ?? ""} disabled={!enabled}><option value="">Sin dirección base</option>{addresses.map((address) => <option key={address.id} value={address.id}>{address.label} · {address.city}</option>)}</select></label>
          </div>
          <button className="primary" disabled={!enabled}>Guardar perfil</button>
        </form>

        <div className="provider-dashboard-card provider-portfolio-panel">
          <div className="provider-card-title"><div><span>▧</span><h2>Portfolio de trabajos</h2></div><small>{profile?.portfolio.length ?? 0}/12</small></div>
          <p className="provider-panel-intro">Registrá casos reales sin incluir datos privados de clientes. Las imágenes se incorporarán mediante almacenamiento controlado.</p>
          {profile?.portfolio.length ? <div className="provider-portfolio-list">{profile.portfolio.map((item) => <article key={item.id}><div><b>{item.title}</b><p>{item.description}</p></div><form action={removePortfolioItem}><input type="hidden" name="item_id" value={item.id} /><button disabled={!enabled} aria-label={`Eliminar ${item.title}`}>×</button></form></article>)}</div> : <div className="provider-mini-empty"><span>◇</span><p>Todavía no agregaste trabajos al portfolio.</p></div>}
          <form action={createPortfolioItem} className="provider-portfolio-form"><label>Título del trabajo<input name="title" minLength={2} maxLength={140} required disabled={!enabled} /></label><label>Descripción<textarea name="description" rows={4} minLength={10} maxLength={2000} required disabled={!enabled}></textarea></label><button className="secondary" disabled={!enabled}>Agregar al portfolio</button></form>
        </div>
      </section>
    </ProviderShell>
  );
}
