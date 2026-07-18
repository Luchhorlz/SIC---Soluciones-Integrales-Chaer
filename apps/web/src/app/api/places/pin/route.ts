import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { signAddressSelection, verifyAddressSelection } from "@/lib/address-selection-token";
import { consumePlacesQuota } from "@/lib/places-rate-limit";

const maximumCorrectionMeters = 500;

function distanceMeters(from: { latitude: number; longitude: number }, to: { latitude: number; longitude: number }): number {
  const radians = Math.PI / 180;
  const deltaLatitude = (to.latitude - from.latitude) * radians;
  const deltaLongitude = (to.longitude - from.longitude) * radians;
  const latitude1 = from.latitude * radians;
  const latitude2 = to.latitude * radians;
  const haversine = Math.sin(deltaLatitude / 2) ** 2 + Math.cos(latitude1) * Math.cos(latitude2) * Math.sin(deltaLongitude / 2) ** 2;
  return 6_371_000 * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId) return NextResponse.json({ error: "Necesitás iniciar sesión." }, { status: 401 });
  if (!consumePlacesQuota(`${session.user.id}:${session.internalSessionId}`)) return NextResponse.json({ error: "Realizaste demasiados ajustes. Esperá un momento." }, { status: 429 });
  try {
    const body = await request.json() as { selectionToken?: unknown; latitude?: unknown; longitude?: unknown };
    if (typeof body.selectionToken !== "string" || typeof body.latitude !== "number" || typeof body.longitude !== "number"
      || !Number.isFinite(body.latitude) || !Number.isFinite(body.longitude) || body.latitude < -90 || body.latitude > 90 || body.longitude < -180 || body.longitude > 180) {
      return NextResponse.json({ error: "El punto seleccionado no es válido." }, { status: 400 });
    }
    const selection = await verifyAddressSelection(body.selectionToken, { userId: session.user.id, sessionId: session.internalSessionId });
    if (distanceMeters({ latitude: selection.anchorLatitude, longitude: selection.anchorLongitude }, { latitude: body.latitude, longitude: body.longitude }) > maximumCorrectionMeters) {
      return NextResponse.json({ error: "El punto debe mantenerse a menos de 500 metros de la dirección elegida." }, { status: 422 });
    }
    const address = { ...selection.address, latitude: body.latitude, longitude: body.longitude };
    const selectionToken = await signAddressSelection({ userId: session.user.id, sessionId: session.internalSessionId, address, anchorLatitude: selection.anchorLatitude, anchorLongitude: selection.anchorLongitude });
    return NextResponse.json({ address, selectionToken });
  } catch {
    return NextResponse.json({ error: "La selección venció o no es válida." }, { status: 400 });
  }
}
