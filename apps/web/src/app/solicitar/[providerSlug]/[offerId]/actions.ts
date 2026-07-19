"use server";

import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { createClientServiceRequest, uploadRequestAttachment } from "@/lib/internal-api";

const modalities = ["AT_CLIENT_ADDRESS", "REMOTE", "HYBRID", "AT_PROVIDER_LOCATION", "PICKUP_DELIVERY"] as const;

function field(formData: FormData, name: string) {
  return String(formData.get(name) ?? "").trim();
}

function argentinaDateTime(value: string): string | null {
  if (!value) return null;
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error("Fecha inválida");
  return new Date(`${value}:00-03:00`).toISOString();
}

export async function submitServiceRequest(formData: FormData) {
  const returnPath = `/solicitar/${encodeURIComponent(field(formData, "provider_slug"))}/${encodeURIComponent(field(formData, "offer_id"))}`;
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId || !session.user.roles.includes("CLIENT")) redirect(`/ingresar?callbackUrl=${encodeURIComponent(returnPath)}`);
  const modality = field(formData, "selected_modality");
  if (!modalities.includes(modality as typeof modalities[number])) redirect(`${returnPath}?error=modality`);
  const files = formData.getAll("attachments").filter((item): item is File => item instanceof File && item.size > 0);
  if (files.length > 5 || files.some((file) => file.size > 10 * 1024 * 1024)) redirect(`${returnPath}?error=attachments`);
  let requestId: string;
  try {
    const authInput = { userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId };
    const request = await createClientServiceRequest({
      ...authInput,
      body: {
        provider_service_id: field(formData, "offer_id"),
        selected_modality: modality as typeof modalities[number],
        client_address_id: field(formData, "client_address_id") || null,
        title: field(formData, "title"),
        description: field(formData, "description"),
        preferred_start_at: argentinaDateTime(field(formData, "preferred_start_at")),
      },
    });
    requestId = request.id;
  } catch {
    redirect(`${returnPath}?error=request`);
  }
  let attachmentWarning = false;
  const authInput = { userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId };
  for (const file of files) {
    try { await uploadRequestAttachment({ ...authInput, requestId, file }); } catch { attachmentWarning = true; }
  }
  if (attachmentWarning) redirect("/cuenta/contrataciones?status=requested&warning=attachments");
  redirect("/cuenta/contrataciones?status=requested");
}
