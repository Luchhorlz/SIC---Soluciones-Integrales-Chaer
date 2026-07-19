import "server-only";

import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { isApplicationAuthConfigured } from "@/lib/auth-config";
import { getProviderProfile, type ProviderProfile } from "@/lib/internal-api";

export type ProviderAuthInput = { userId: string; roles: string[]; sessionId: string };

export async function providerPageContext(options: { requireProfile?: boolean } = {}) {
  const configured = isApplicationAuthConfigured();
  const session = configured ? await auth() : null;
  if (configured && !session?.user) redirect("/ingresar");
  if (configured && !session?.user.roles.includes("PROVIDER")) redirect("/onboarding/rol");

  const input: ProviderAuthInput | null = session?.user
    ? { userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId }
    : null;
  let profile: ProviderProfile | null = null;
  let apiUnavailable = false;
  if (input) {
    try {
      profile = await getProviderProfile(input);
    } catch {
      apiUnavailable = true;
    }
  }
  if (configured && options.requireProfile && !apiUnavailable && !profile) redirect("/onboarding/prestador");
  return { configured, input, profile, apiUnavailable };
}
