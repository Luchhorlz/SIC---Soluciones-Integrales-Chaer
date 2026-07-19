"use client";

import { useState } from "react";

export function PublicSearchForm({ initialQuery = "", initialMode = "ALL", initialLatitude, initialLongitude, compact = false }: { initialQuery?: string; initialMode?: string; initialLatitude?: string; initialLongitude?: string; compact?: boolean }) {
  const [latitude, setLatitude] = useState(initialLatitude ?? "");
  const [longitude, setLongitude] = useState(initialLongitude ?? "");
  const [locationMessage, setLocationMessage] = useState(latitude ? "Ubicación aproximada activada" : "Sin ubicación: se mostrarán opciones remotas");

  function locate() {
    if (!navigator.geolocation) {
      setLocationMessage("Este navegador no permite obtener ubicación");
      return;
    }
    setLocationMessage("Obteniendo ubicación…");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude.toFixed(6));
        setLongitude(position.coords.longitude.toFixed(6));
        setLocationMessage("Ubicación aproximada activada");
      },
      () => setLocationMessage("No se pudo usar la ubicación. Podés buscar servicios remotos."),
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 },
    );
  }

  return (
    <form className={`public-search-form${compact ? " compact" : ""}`} action="/buscar" method="get">
      <label className="public-search-query"><span aria-hidden="true">⌕</span><input name="q" defaultValue={initialQuery} minLength={2} maxLength={160} placeholder="¿Qué servicio necesitás?" aria-label="Servicio a buscar" required /></label>
      <input type="hidden" name="latitude" value={latitude} readOnly />
      <input type="hidden" name="longitude" value={longitude} readOnly />
      <button className={`public-location-button${latitude ? " active" : ""}`} type="button" onClick={locate}><span aria-hidden="true">⌖</span><span>{locationMessage}</span></button>
      <label className="sr-only" htmlFor={`search-mode-${compact ? "compact" : "full"}`}>Modalidad</label>
      <select id={`search-mode-${compact ? "compact" : "full"}`} name="mode" defaultValue={initialMode}>
        <option value="ALL">Todas</option>
        <option value="NEARBY">Cerca mío</option>
        <option value="REMOTE">Remoto</option>
        <option value="HYBRID">Híbrido</option>
      </select>
      <button className="primary" type="submit">Buscar</button>
    </form>
  );
}
