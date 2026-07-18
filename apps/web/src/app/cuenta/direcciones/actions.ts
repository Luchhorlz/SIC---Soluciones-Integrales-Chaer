"use server";

import { revalidatePath } from "next/cache";

import { auth } from "@/auth";
import { createUserAddress } from "@/lib/internal-api";

export type AddressActionState = { error: string | null; success: boolean };

export async function saveAddress(_state: AddressActionState, formData: FormData): Promise<AddressActionState> {
  const configured = Boolean(process.env.GOOGLE_MAPS_API_KEY && process.env.INTERNAL_API_JWT_SECRET);
  if (!configured) return { error: "La ubicación se habilitará cuando Google Maps esté configurado.", success: false };
  const placeId = String(formData.get("google_place_id") ?? "").trim();
  const latitudeValue = String(formData.get("latitude") ?? "").trim();
  const longitudeValue = String(formData.get("longitude") ?? "").trim();
  const latitude = Number(latitudeValue);
  const longitude = Number(longitudeValue);
  if (!placeId || !latitudeValue || !longitudeValue || !Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    return { error: "Seleccioná una dirección válida de Google Places.", success: false };
  }
  const session = await auth();
  if (!session?.user?.id) return { error: "Tu sesión no es válida.", success: false };
  try {
    await createUserAddress({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId, address: { label: String(formData.get("label") ?? ""), formatted_address: String(formData.get("formatted_address") ?? ""), street: String(formData.get("street") ?? ""), street_number: String(formData.get("street_number") ?? ""), unit: String(formData.get("unit") ?? "") || null, city: String(formData.get("city") ?? ""), province: String(formData.get("province") ?? ""), postal_code: String(formData.get("postal_code") ?? "") || null, country_code: "AR", google_place_id: placeId, latitude, longitude, is_default: formData.get("is_default") === "on" } });
  } catch {
    return { error: "No pudimos guardar la dirección. Verificá los datos e intentá nuevamente.", success: false };
  }
  revalidatePath("/cuenta/direcciones");
  return { error: null, success: true };
}
