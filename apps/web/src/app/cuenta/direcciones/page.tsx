import { auth } from "@/auth";
import { getUserAddresses, type UserAddress } from "@/lib/internal-api";

import { AddressForm } from "./address-form";

export const metadata = { title: "Mis direcciones | SIC" };

export default async function AddressesPage() {
  const configured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET);
  const mapsReady = Boolean(process.env.GOOGLE_MAPS_API_KEY);
  const placesAutocompleteReady = false;
  const session = configured ? await auth() : null;
  let addresses: UserAddress[] = [];
  if (session?.user?.id) {
    try { addresses = await getUserAddresses({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId }); } catch { addresses = []; }
  }
  return <>
    <div className="account-top address-top"><div><p className="eyebrow">PRIVACIDAD Y COBERTURA</p><h1>Mis direcciones</h1><p>Guardá los lugares donde podrías necesitar un servicio presencial.</p></div><AddressForm enabled={configured && mapsReady && placesAutocompleteReady} /></div>
    {!placesAutocompleteReady && <div className="preview-notice account-preview">Vista previa activa. La búsqueda se habilitará cuando conectemos Google Places en la próxima etapa.</div>}
    <div className="address-layout"><section className="address-list"><div className="address-section-title"><h2>Direcciones guardadas</h2><span>{addresses.length}</span></div>{addresses.length ? addresses.map((address) => <article className="address-card" key={address.id}><div className="address-pin">⌖</div><div><div className="address-name"><h3>{address.label}</h3>{address.is_default && <span>Predeterminada</span>}</div><p>{address.formatted_address}</p><small>{address.city}, {address.province}</small></div><button aria-label={`Editar ${address.label}`}>⋮</button></article>) : <div className="address-empty"><span>⌖</span><h3>Todavía no guardaste direcciones</h3><p>Cuando agregues una, SIC podrá mostrarte prestadores que realmente lleguen hasta tu zona.</p></div>}</section><aside className="address-map-placeholder"><div className="map-grid"></div><div className="map-message"><span>♢</span><b>Ubicación protegida</b><p>El mapa nunca muestra públicamente tu domicilio exacto.</p></div></aside></div>
  </>;
}
