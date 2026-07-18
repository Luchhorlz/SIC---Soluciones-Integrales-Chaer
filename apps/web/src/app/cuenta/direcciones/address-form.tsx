"use client";

import { useActionState, useEffect, useState } from "react";

import type { NormalizedGoogleAddress, PlaceSuggestion } from "@/lib/google-places";

import { saveAddress, type AddressActionState } from "./actions";
import { AddressMapPicker } from "./address-map-picker";

const initialState: AddressActionState = { error: null, success: false };

type DetailsResponse = { address?: NormalizedGoogleAddress; selectionToken?: string; error?: string };

export function AddressForm({ enabled, mapEnabled }: { enabled: boolean; mapEnabled: boolean }) {
  const [open, setOpen] = useState(false);
  return open
    ? <AddressFormDialog enabled={enabled} mapEnabled={mapEnabled} onClose={() => setOpen(false)} />
    : <button className="primary small" onClick={() => setOpen(true)}>+ Agregar dirección</button>;
}

function AddressFormDialog({ enabled, mapEnabled, onClose }: { enabled: boolean; mapEnabled: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const [sessionToken, setSessionToken] = useState(() => globalThis.crypto.randomUUID());
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [selected, setSelected] = useState<NormalizedGoogleAddress | null>(null);
  const [selectionToken, setSelectionToken] = useState("");
  const [searching, setSearching] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [state, action, pending] = useActionState(saveAddress, initialState);

  useEffect(() => {
    if (!enabled || selected || query.trim().length < 3) return;
    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      setSearching(true);
      setLookupError(null);
      try {
        const response = await fetch("/api/places/autocomplete", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ input: query, sessionToken }),
          signal: controller.signal,
        });
        const payload = await response.json() as { suggestions?: PlaceSuggestion[]; error?: string };
        if (!response.ok) throw new Error(payload.error || "No pudimos buscar direcciones.");
        setSuggestions(payload.suggestions ?? []);
      } catch (error) {
        if (!controller.signal.aborted) setLookupError(error instanceof Error ? error.message : "No pudimos buscar direcciones.");
      } finally {
        if (!controller.signal.aborted) setSearching(false);
      }
    }, 350);
    return () => {
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [enabled, query, selected, sessionToken]);

  function changeQuery(value: string) {
    if (selected) setSessionToken(globalThis.crypto.randomUUID());
    setQuery(value);
    setSelected(null);
    setSelectionToken("");
    setSuggestions([]);
    setLookupError(null);
  }

  async function chooseSuggestion(suggestion: PlaceSuggestion) {
    setSearching(true);
    setLookupError(null);
    setSuggestions([]);
    try {
      const response = await fetch("/api/places/details", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ placeId: suggestion.placeId, sessionToken }),
      });
      const payload = await response.json() as DetailsResponse;
      if (!response.ok || !payload.address || !payload.selectionToken) throw new Error(payload.error || "No pudimos confirmar esa dirección.");
      setSelected(payload.address);
      setSelectionToken(payload.selectionToken);
      setQuery(payload.address.formatted_address);
    } catch (error) {
      setSessionToken(globalThis.crypto.randomUUID());
      setLookupError(error instanceof Error ? error.message : "No pudimos confirmar esa dirección.");
    } finally {
      setSearching(false);
    }
  }

  return <div className="address-form-overlay" role="dialog" aria-modal="true" aria-label="Agregar dirección" onKeyDown={(event) => { if (event.key === "Escape") onClose(); }}><form action={action} className="address-form">
    <div className="address-form-title"><div><p className="eyebrow">NUEVA DIRECCIÓN</p><h2>¿Dónde necesitás el servicio?</h2></div><button type="button" onClick={onClose} aria-label="Cerrar" autoFocus={!enabled}>×</button></div>
    <div className="address-autocomplete">
      <label className="address-search"><span>⌕</span><input value={query} onChange={(event) => changeQuery(event.target.value)} placeholder="Buscá una calle y altura" disabled={!enabled || state.success} role="combobox" aria-autocomplete="list" aria-expanded={suggestions.length > 0} aria-controls="address-suggestions" autoFocus={enabled} /><small>{searching ? "Buscando…" : enabled ? "Elegí una sugerencia para confirmar la ubicación." : "La búsqueda automática espera la configuración privada de Google Places."}</small></label>
      {suggestions.length > 0 && <div className="address-suggestions" id="address-suggestions" role="listbox">{suggestions.map((suggestion) => <button key={suggestion.placeId} type="button" role="option" aria-selected="false" onClick={() => chooseSuggestion(suggestion)}><span>⌖</span><span><b>{suggestion.mainText}</b><small>{suggestion.secondaryText}</small></span></button>)}</div>}
    </div>
    {lookupError && <p className="form-error" role="alert">{lookupError}</p>}
    <div className="address-fields"><label>Nombre para identificarla<input name="label" placeholder="Casa, trabajo…" disabled={!selected || state.success} required /></label><label>Calle<input value={selected?.street ?? ""} readOnly aria-readonly="true" /></label><label>Altura<input value={selected?.street_number ?? ""} readOnly aria-readonly="true" /></label><label>Piso / departamento<input name="unit" disabled={!selected || state.success} /></label><label>Localidad<input value={selected?.city ?? ""} readOnly aria-readonly="true" /></label><label>Provincia<input value={selected?.province ?? ""} readOnly aria-readonly="true" /></label><label>Código postal<input value={selected?.postal_code ?? ""} readOnly aria-readonly="true" /></label></div>
    {selected && !state.success && <AddressMapPicker key={selected.google_place_id} enabled={mapEnabled} address={selected} selectionToken={selectionToken} onCorrect={(address, token) => { setSelected(address); setSelectionToken(token); }} />}
    <input type="hidden" name="address_selection_token" value={selectionToken} />
    <label className="default-check"><input type="checkbox" name="is_default" disabled={!selected || state.success} /> Usar como dirección predeterminada</label>
    <div className="privacy-note"><span>♢</span><p><b>Tu dirección es privada.</b> Solo se comparte con el prestador involucrado cuando una contratación lo requiere.</p></div>
    {state.error && <p className="form-error" role="alert">{state.error}</p>}{state.success && <p className="form-success">Dirección guardada correctamente.</p>}
    <div className="address-actions"><button className="secondary" type="button" onClick={onClose}>{state.success ? "Cerrar" : "Cancelar"}</button><button className="primary" disabled={!enabled || !selectionToken || pending || state.success}>{pending ? "Guardando…" : "Guardar dirección"}</button></div>
  </form></div>;
}
