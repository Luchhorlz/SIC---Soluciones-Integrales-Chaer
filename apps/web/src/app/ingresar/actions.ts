"use server";

import { AuthError } from "next-auth";
import { redirect } from "next/navigation";

import { signIn, signOut } from "@/auth";
import { demoAccounts } from "@/lib/demo-accounts";

export async function signInWithGoogle() {
  await signIn("google", { redirectTo: "/onboarding/rol" });
}

export async function signInWithDemo(formData: FormData) {
  const username = String(formData.get("username") ?? "").trim().toLowerCase();
  const account = demoAccounts.find((item) => item.username === username);
  if (!account) redirect("/ingresar?demo_error=1");
  try {
    await signIn("credentials", { username, password: String(formData.get("password") ?? ""), redirectTo: account.redirectTo });
  } catch (error) {
    if (error instanceof AuthError) redirect("/ingresar?demo_error=1");
    throw error;
  }
}

export async function signOutFromSic() {
  await signOut({ redirectTo: "/ingresar" });
}
