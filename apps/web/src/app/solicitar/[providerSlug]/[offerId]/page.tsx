import Link from "next/link";
import { notFound } from "next/navigation";

import { auth } from "@/auth";
import { PublicFooter, PublicHeader } from "@/components/public-header";
import { isApplicationAuthConfigured } from "@/lib/auth-config";
import { getUserAddresses, type UserAddress } from "@/lib/internal-api";
import { formatOfferPrice, getPublicProvider, modalityLabel } from "@/lib/public-search";

import { submitServiceRequest } from "./actions";

export const dynamic = "force-dynamic";
export const metadata = { title: "Solicitar servicio | SIC", robots: { index: false, follow: false } };
type Props = { params: Promise<{ providerSlug: string; offerId: string }>; searchParams: Promise<{ error?: string }> };

export default async function RequestServicePage({ params, searchParams }: Props) {
  const { providerSlug, offerId } = await params;
  const query = await searchParams;
  const { profile, apiUnavailable } = await getPublicProvider(providerSlug);
  if (!profile && !apiUnavailable) notFound();
  const offer = profile?.services.find((item) => item.id === offerId);
  if (profile && !offer) notFound();
  const configured = isApplicationAuthConfigured();
  const session = configured ? await auth() : null;
  let addresses: UserAddress[] = [];
  if (session?.user?.roles.includes("CLIENT")) {
    try { addresses = await getUserAddresses({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId }); } catch { addresses = []; }
  }
  const enabled = Boolean(configured && session?.user?.roles.includes("CLIENT") && offer);

  return <main><PublicHeader />
    {!offer ? <section className="public-unavailable"><span>◷</span><h1>No pudimos abrir esta solicitud</h1><p>La base privada no está conectada en esta previsualización. Cuando el entorno tenga PostgreSQL y autenticación podrás probar el flujo completo.</p><Link className="secondary" href={`/prestador/${providerSlug}`}>Volver al perfil</Link></section> : <section className="request-page">
      <div className="public-breadcrumbs"><Link href={`/prestador/${profile!.slug}`}>{profile!.display_name}</Link><span>›</span><b>Solicitud privada</b></div>
      <div className="request-layout">
        <div><p className="eyebrow">CONTRATACIÓN SIC</p><h1>Contale qué necesitás</h1><p className="lead">El prestador recibirá esta solicitud en su panel privado. No se publica como anuncio ni queda visible para terceros.</p>
          {!configured && <div className="preview-notice">Vista previa: para enviar necesitás configurar la autenticación y la API privada.</div>}
          {configured && !session?.user && <div className="preview-notice">Ingresá a SIC para enviar la solicitud.</div>}
          {query.error && <div className="form-error">No pudimos enviar la solicitud. Revisá los datos, la cobertura y los archivos.</div>}
          <form className="request-form" action={submitServiceRequest}>
            <input type="hidden" name="provider_slug" value={providerSlug} /><input type="hidden" name="offer_id" value={offer.id} />
            <label>¿Cómo querés recibir el servicio?<select name="selected_modality" required disabled={!enabled}>{offer.modalities.map((modality) => <option key={modality} value={modality}>{modalityLabel(modality)}</option>)}</select></label>
            <label>Dirección guardada <select name="client_address_id" disabled={!enabled}><option value="">No corresponde / elegir después</option>{addresses.map((address) => <option key={address.id} value={address.id}>{address.label} — {address.formatted_address}</option>)}</select><small>Es obligatoria para domicilio, modalidad híbrida o retiro y entrega.</small></label>
            <label>Asunto<input name="title" minLength={4} maxLength={180} required placeholder="Ej.: Pérdida debajo de la pileta" disabled={!enabled} /></label>
            <label>Detalle<textarea name="description" minLength={20} maxLength={5000} required placeholder="Describí el problema, medidas, acceso y todo lo que ayude a evaluarlo." disabled={!enabled}></textarea></label>
            <label>Fecha y hora preferida <input name="preferred_start_at" type="datetime-local" disabled={!enabled} /><small>Es una preferencia; la confirmación final crea el turno.</small></label>
            <label>Fotos o documentos <input name="attachments" type="file" accept="image/png,image/jpeg,application/pdf" multiple disabled={!enabled} /><small>Hasta 5 archivos privados. Se validan y analizan antes de habilitarse.</small></label>
            <button className="primary" disabled={!enabled}>Enviar solicitud privada</button>
          </form>
        </div>
        <aside className="request-summary"><p className="eyebrow">OFERTA ELEGIDA</p><h2>{offer.headline}</h2><b>{formatOfferPrice(offer)}</b><p>{offer.description}</p><ul><li><span>Servicio</span><b>{offer.service_name}</b></li><li><span>Prestador</span><b>{profile!.display_name}</b></li><li><span>Modalidades</span><b>{offer.modalities.map(modalityLabel).join(" · ")}</b></li></ul><div>⌖ La dirección exacta se cifra al confirmar el turno.</div></aside>
      </div>
    </section>}
    <PublicFooter />
  </main>;
}
