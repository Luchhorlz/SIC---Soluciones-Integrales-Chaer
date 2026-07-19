"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { setClientFavorite } from "@/lib/internal-api";

export async function toggleFavorite(formData: FormData) {
  const slug = String(formData.get("provider_slug") ?? "").trim();
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 220) throw new Error("Invalid provider slug");
  const favorite = String(formData.get("favorite") ?? "") === "true";
  const requestedReturn = String(formData.get("return_path") ?? "");
  const returnPath = requestedReturn === "/cuenta/favoritos" || requestedReturn === `/prestador/${slug}` ? requestedReturn : "/cuenta/favoritos";
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId || !session.user.roles.includes("CLIENT")) redirect(`/ingresar?callbackUrl=${encodeURIComponent(returnPath)}`);
  try { await setClientFavorite({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId, providerSlug: slug, favorite }); }
  catch { redirect(`${returnPath}?error=favorite`); }
  revalidatePath(returnPath); revalidatePath("/cuenta/favoritos"); redirect(`${returnPath}?favorite=${favorite ? "saved" : "removed"}`);
}
