"use server";

import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { replaceUserRoles } from "@/lib/internal-api";

export type RoleActionState = { error: string | null };

export async function saveRoles(_state: RoleActionState, formData: FormData): Promise<RoleActionState> {
  const configured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET);
  if (!configured) return { error: "La persistencia se habilitará cuando las credenciales privadas estén configuradas." };

  const session = await auth();
  if (!session?.user?.id) return { error: "Tu sesión no es válida. Volvé a ingresar con Google." };

  const selectedRoles = formData.getAll("roles").map(String);
  if (!selectedRoles.length || selectedRoles.some((role) => role !== "CLIENT" && role !== "PROVIDER")) return { error: "Elegí al menos una opción válida." };

  try {
    await replaceUserRoles({ userId: session.user.id, currentRoles: session.user.roles, selectedRoles, sessionId: "authjs-session" });
  } catch {
    return { error: "No pudimos guardar los roles. Revisá que la base de datos y la API estén disponibles." };
  }
  redirect("/cuenta");
}
