"use server";

import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { isApplicationAuthConfigured } from "@/lib/auth-config";
import { replaceUserRoles } from "@/lib/internal-api";

export type RoleActionState = { error: string | null };

export async function saveRoles(_state: RoleActionState, formData: FormData): Promise<RoleActionState> {
  const configured = isApplicationAuthConfigured();
  if (!configured) return { error: "La persistencia se habilitará cuando las credenciales privadas estén configuradas." };

  const session = await auth();
  if (!session?.user?.id) return { error: "Tu sesión no es válida. Volvé a ingresar." };
  if (session.isDemo) return { error: "Las cuentas demo tienen un rol fijo para que puedas recorrer cada panel." };

  const selectedRoles = formData.getAll("roles").map(String);
  if (!selectedRoles.length || selectedRoles.some((role) => role !== "CLIENT" && role !== "PROVIDER")) return { error: "Elegí al menos una opción válida." };

  try {
    await replaceUserRoles({ userId: session.user.id, currentRoles: session.user.roles, selectedRoles, sessionId: session.internalSessionId });
  } catch {
    return { error: "No pudimos guardar los roles. Revisá que la base de datos y la API estén disponibles." };
  }
  redirect(selectedRoles.includes("PROVIDER") ? "/onboarding/prestador" : "/cuenta");
}
