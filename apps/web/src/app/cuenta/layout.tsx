import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { AccountSidebar } from "@/components/account-sidebar";

export default async function AccountLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const configured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET);
  const session = configured ? await auth() : null;
  if (configured && !session?.user) redirect("/ingresar");
  if (configured && session?.user && !session.user.roles.includes("CLIENT")) redirect("/onboarding/rol");
  return <main className="account-shell"><AccountSidebar /><section className="account-main">{children}</section></main>;
}
