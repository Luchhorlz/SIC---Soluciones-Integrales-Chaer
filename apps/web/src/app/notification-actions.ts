"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { markNotificationRead } from "@/lib/internal-api";

const allowedPaths = new Set(["/cuenta/notificaciones", "/prestador/notificaciones"]);

export async function updateNotification(formData: FormData) {
  const session = await auth(); const returnPath = String(formData.get("return_path") ?? "");
  if (!allowedPaths.has(returnPath)) throw new Error("Invalid return path");
  if (!session?.user?.id || !session.internalSessionId) redirect("/ingresar");
  try {
    await markNotificationRead({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId, notificationId: String(formData.get("notification_id") ?? "") || undefined });
  } catch { redirect(`${returnPath}?error=notification`); }
  revalidatePath(returnPath); redirect(returnPath);
}
