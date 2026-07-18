"use client";

import { useActionState, useState } from "react";

import { saveAddress, type AddressActionState } from "./actions";

const initialState: AddressActionState = { error: null, success: false };

export function AddressForm({ enabled }: { enabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [state, action, pending] = useActionState(saveAddress, initialState);
  if (!open) return <button className="primary small" onClick={() => setOpen(true)}>+ Agregar dirección</button>;
  return <div className="address-form-overlay" role="dialog" aria-modal="true" aria-label="Agregar dirección"><form action={action} className="address-form">
    <div className="address-form-title"><div><p className="eyebrow">NUEVA DIRECCIÓN</p><h2>¿Dónde necesitás el servicio?</h2></div><button type="button" onClick={() => setOpen(false)} aria-label="Cerrar">×</button></div>
    <label className="address-search"><span>⌕</span><input name="formatted_address" placeholder="Buscá una calle y altura" disabled={!enabled} required /><small>{enabled ? "Elegí una sugerencia para confirmar la ubicación." : "La búsqueda automática espera la clave privada de Google Maps."}</small></label>
    <div className="address-fields"><label>Nombre para identificarla<input name="label" placeholder="Casa, trabajo…" required /></label><label>Calle<input name="street" required /></label><label>Altura<input name="street_number" required /></label><label>Piso / departamento<input name="unit" /></label><label>Localidad<input name="city" required /></label><label>Provincia<input name="province" defaultValue="Buenos Aires" required /></label><label>Código postal<input name="postal_code" /></label></div>
    <input type="hidden" name="google_place_id" /><input type="hidden" name="latitude" /><input type="hidden" name="longitude" />
    <label className="default-check"><input type="checkbox" name="is_default" /> Usar como dirección predeterminada</label>
    <div className="privacy-note"><span>♢</span><p><b>Tu dirección es privada.</b> Solo se comparte con el prestador involucrado cuando una contratación lo requiere.</p></div>
    {state.error && <p className="form-error" role="alert">{state.error}</p>}{state.success && <p className="form-success">Dirección guardada.</p>}
    <div className="address-actions"><button className="secondary" type="button" onClick={() => setOpen(false)}>Cancelar</button><button className="primary" disabled={!enabled || pending}>{pending ? "Guardando…" : "Guardar dirección"}</button></div>
  </form></div>;
}
