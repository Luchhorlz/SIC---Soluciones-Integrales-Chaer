"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

import type { NormalizedGoogleAddress } from "@/lib/google-places";

const mapWidth = 640;
const mapHeight = 360;
const zoom = 17;

function worldPoint(latitude: number, longitude: number): { x: number; y: number } {
  const scale = 256 * 2 ** zoom;
  const sine = Math.min(Math.max(Math.sin(latitude * Math.PI / 180), -0.9999), 0.9999);
  return { x: (longitude + 180) / 360 * scale, y: (0.5 - Math.log((1 + sine) / (1 - sine)) / (4 * Math.PI)) * scale };
}

function coordinates(point: { x: number; y: number }): { latitude: number; longitude: number } {
  const scale = 256 * 2 ** zoom;
  const longitude = point.x / scale * 360 - 180;
  const latitude = Math.atan(Math.sinh(Math.PI - 2 * Math.PI * point.y / scale)) * 180 / Math.PI;
  return { latitude, longitude };
}

export function AddressMapPicker({ enabled, address, selectionToken, onCorrect }: { enabled: boolean; address: NormalizedGoogleAddress; selectionToken: string; onCorrect: (address: NormalizedGoogleAddress, selectionToken: string) => void }) {
  const [initialToken] = useState(selectionToken);
  const [center] = useState({ latitude: address.latitude, longitude: address.longitude });
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adjusting, setAdjusting] = useState(false);
  const [pin, setPin] = useState({ x: mapWidth / 2, y: mapHeight / 2 });

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    let objectUrl = "";
    void (async () => {
      try {
        const response = await fetch("/api/places/map", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ selectionToken: initialToken }) });
        if (!response.ok) {
          const payload = await response.json() as { error?: string };
          throw new Error(payload.error || "No pudimos cargar el mapa.");
        }
        objectUrl = URL.createObjectURL(await response.blob());
        if (active) setImageUrl(objectUrl);
      } catch (mapError) {
        if (active) setError(mapError instanceof Error ? mapError.message : "No pudimos cargar el mapa.");
      }
    })();
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [enabled, initialToken]);

  async function correctPin(nextPin: { x: number; y: number }) {
    if (adjusting) return;
    setAdjusting(true);
    setError(null);
    const origin = worldPoint(center.latitude, center.longitude);
    const corrected = coordinates({ x: origin.x + nextPin.x - mapWidth / 2, y: origin.y + nextPin.y - mapHeight / 2 });
    try {
      const response = await fetch("/api/places/pin", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ selectionToken, ...corrected }) });
      const payload = await response.json() as { address?: NormalizedGoogleAddress; selectionToken?: string; error?: string };
      if (!response.ok || !payload.address || !payload.selectionToken) throw new Error(payload.error || "No pudimos ajustar el punto.");
      setPin(nextPin);
      onCorrect(payload.address, payload.selectionToken);
    } catch (pinError) {
      setError(pinError instanceof Error ? pinError.message : "No pudimos ajustar el punto.");
    } finally {
      setAdjusting(false);
    }
  }

  function clickMap(event: React.MouseEvent<HTMLButtonElement>) {
    if (!imageUrl || event.detail === 0) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    void correctPin({ x: (event.clientX - bounds.left) / bounds.width * mapWidth, y: (event.clientY - bounds.top) / bounds.height * mapHeight });
  }

  function moveWithKeyboard(event: React.KeyboardEvent<HTMLButtonElement>) {
    const movement: Record<string, { x: number; y: number }> = { ArrowLeft: { x: -8, y: 0 }, ArrowRight: { x: 8, y: 0 }, ArrowUp: { x: 0, y: -8 }, ArrowDown: { x: 0, y: 8 } };
    const delta = movement[event.key];
    if (!delta || !imageUrl) return;
    event.preventDefault();
    void correctPin({ x: Math.min(mapWidth, Math.max(0, pin.x + delta.x)), y: Math.min(mapHeight, Math.max(0, pin.y + delta.y)) });
  }

  if (!enabled) return <div className="address-map-unavailable"><span>⌖</span><p>El ajuste sobre mapa se habilita con Maps Static API y su firma privada.</p></div>;
  return <div className="address-pin-editor"><div className="address-pin-editor-title"><b>Ajustá el punto exacto</b><small>Hacé clic en el mapa o usá las flechas del teclado.</small></div>{imageUrl ? <button type="button" className="address-map-button" onClick={clickMap} onKeyDown={moveWithKeyboard} aria-label="Mapa para ajustar el punto exacto de la dirección"><Image src={imageUrl} alt="" fill sizes="(max-width: 850px) 90vw, 760px" unoptimized /><span className="address-map-pin" style={{ left: `${pin.x / mapWidth * 100}%`, top: `${pin.y / mapHeight * 100}%` }}>⌖</span>{adjusting && <span className="address-map-loading">Ajustando…</span>}</button> : <div className="address-map-loading-panel">{error ?? "Cargando mapa…"}</div>}{error && imageUrl && <p className="form-error" role="alert">{error}</p>}</div>;
}
