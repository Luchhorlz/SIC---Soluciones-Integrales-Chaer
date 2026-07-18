"use server";

import { revalidatePath } from "next/cache";

import { auth } from "@/auth";
import { verifyAddressSelection } from "@/lib/address-selection-token";
import { createUserAddress } from "@/lib/internal-api";

export type AddressActionState = { error: string | null; success: boolean };

export async function saveAddress(_state: AddressActionState, formData: FormData): Promise<AddressActionState> {
  if (!process.env.INTERNAL_API_JWT_SECRET) return { error: "El guardado todavía no está configurado.", success: false };
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId) return { error: "Tu sesión no es válida.", success: false };
  const label = String(formData.get("label") ?? "").trim();
  const unit = String(formData.get("unit") ?? "").trim();
  const selectionToken = String(formData.get("address_selection_token") ?? "").trim();
  if (!label || label.length > 80) return { error: "Ingresá un nombre de hasta 80 caracteres.", success: false };
  if (unit.length > 50) return { error: "El piso o departamento no puede superar 50 caracteres.", success: false };
  if (!selectionToken) return { error: "Seleccioná una dirección válida de la lista.", success: false };
  let address;
  try {
    address = (await verifyAddressSelection(selectionToken, { userId: session.user.id, sessionId: session.internalSessionId })).address;
  } catch {
    return { error: "La selección venció o fue modificada. Buscá la dirección nuevamente.", success: false };
  }
  try {
    await createUserAddress({
      userId: session.user.id,
      roles: session.user.roles,
      sessionId: session.internalSessionId,
      address: { ...address, label, unit: unit || null, is_default: formData.get("is_default") === "on" },
    });
  } catch {
    return { error: "No pudimos guardar la dirección. Intentá nuevamente.", success: false };
  }
  revalidatePath("/cuenta/direcciones");
  return { error: null, success: true };
}
