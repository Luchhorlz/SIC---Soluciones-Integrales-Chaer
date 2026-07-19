"use client";

import { useMemo, useState } from "react";

import type { CatalogService, UserAddress } from "@/lib/internal-api";

import { createOffer } from "../actions";

const modalityOptions = [
  ["AT_CLIENT_ADDRESS", "En el domicilio del cliente"],
  ["REMOTE", "Remoto"],
  ["HYBRID", "Híbrido"],
  ["AT_PROVIDER_LOCATION", "En mi establecimiento"],
  ["PICKUP_DELIVERY", "Retiro y entrega"],
] as const;

const coverageModalities = new Set(["AT_CLIENT_ADDRESS", "HYBRID", "PICKUP_DELIVERY"]);

export function OfferForm({ catalog, addresses, enabled }: { catalog: CatalogService[]; addresses: UserAddress[]; enabled: boolean }) {
  const [query, setQuery] = useState("");
  const [serviceId, setServiceId] = useState("");
  const [selectedModalities, setSelectedModalities] = useState<Set<string>>(new Set());
  const [pricingType, setPricingType] = useState("QUOTE");
  const selected = catalog.find((item) => item.id === serviceId);
  const needsCoverage = [...selectedModalities].some((item) => coverageModalities.has(item));
  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("es-AR");
    return catalog.filter((item) => !normalized || item.name.toLocaleLowerCase("es-AR").includes(normalized)).slice(0, 80);
  }, [catalog, query]);

  function chooseService(nextId: string) {
    setServiceId(nextId);
    const item = catalog.find((candidate) => candidate.id === nextId);
    if (item && !item.allows_quote && item.allows_fixed_price) setPricingType("FIXED");
    else setPricingType("QUOTE");
  }

  function changeModality(modality: string, checked: boolean) {
    setSelectedModalities((current) => {
      const next = new Set(current);
      if (checked) next.add(modality); else next.delete(modality);
      return next;
    });
  }

  return (
    <form action={createOffer} className="provider-dashboard-card provider-offer-form">
      <div className="provider-card-title"><div><span>＋</span><h2>Configurar nuevo servicio</h2></div><small>Catálogo oficial SIC</small></div>
      <label>Buscar aptitud<input value={query} onChange={(event) => setQuery(event.target.value)} disabled={!enabled} placeholder="Ej.: reparación de pérdidas" /></label>
      <label>Servicio<select name="service_id" value={serviceId} onChange={(event) => chooseService(event.target.value)} required disabled={!enabled}><option value="">{catalog.length ? `Seleccionar entre ${catalog.length.toLocaleString("es-AR")} servicios` : "Disponible al conectar PostgreSQL"}</option>{filtered.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <div className="provider-form-grid"><label>Título de tu propuesta<input name="headline" minLength={4} maxLength={180} required disabled={!enabled} placeholder="Cómo ofrecés este servicio" /></label><label>Duración estimada en minutos<input name="estimated_duration_minutes" type="number" min="15" max="43200" disabled={!enabled} /></label><label className="wide">Descripción del servicio<textarea name="description" rows={4} minLength={20} maxLength={4000} required disabled={!enabled}></textarea></label></div>
      <fieldset className="provider-choice-fieldset"><legend>Modalidades disponibles</legend><div>{modalityOptions.map(([value, label]) => <label key={value}><input type="checkbox" name="modalities" value={value} disabled={!enabled} onChange={(event) => changeModality(value, event.target.checked)} />{label}</label>)}</div></fieldset>
      <div className="provider-form-grid"><label>Tipo de precio<select name="pricing_type" value={pricingType} onChange={(event) => setPricingType(event.target.value)} disabled={!enabled || !selected} required>{selected?.allows_quote && <option value="QUOTE">A presupuestar</option>}{selected?.allows_fixed_price && <><option value="FIXED">Precio fijo</option><option value="FROM">Desde</option><option value="HOURLY">Por hora</option><option value="PER_SESSION">Por sesión</option><option value="PER_UNIT">Por unidad</option></>}</select></label>{pricingType !== "QUOTE" && <label>Importe en ARS<input name="price_amount" type="number" min="1" step="0.01" required disabled={!enabled} /></label>}<label>Días de garantía<input name="guarantee_days" type="number" min="0" max="3650" disabled={!enabled} /></label></div>
      <div className="provider-inline-checks"><label><input type="checkbox" name="requires_quote_details" defaultChecked disabled={!enabled} /> Pedir detalles para presupuestar</label><label><input type="checkbox" name="accepts_urgent" disabled={!enabled || !selected?.allows_urgent} /> Aceptar urgencias</label></div>
      {needsCoverage && <section className="provider-coverage-fields"><div><span>◎</span><div><b>Cobertura propia de este servicio</b><p>El centro debe ser una dirección previamente validada.</p></div></div><div className="provider-form-grid"><label>Centro de cobertura<select name="center_address_id" required disabled={!enabled}><option value="">Seleccionar dirección</option>{addresses.map((address) => <option key={address.id} value={address.id}>{address.label} · {address.city}</option>)}</select></label><label>Radio en metros<input name="radius_meters" type="number" min="100" max="1000000" defaultValue="10000" required disabled={!enabled} /></label><label>Radio urgente en metros<input name="urgent_radius_meters" type="number" min="100" max="1000000" disabled={!enabled || !selected?.allows_urgent} /></label></div></section>}
      {selected && <div className="provider-catalog-policy"><span>✓</span><p><b>Reglas del catálogo:</b> {selected.allows_quote ? "admite presupuesto" : "sin presupuesto"}, {selected.allows_fixed_price ? "admite precio directo" : "sin precio directo"} y {selected.allows_urgent ? "admite urgencias" : "sin urgencias"}.</p></div>}
      <button className="primary" disabled={!enabled || !selected || !selectedModalities.size}>Guardar servicio</button>
    </form>
  );
}
