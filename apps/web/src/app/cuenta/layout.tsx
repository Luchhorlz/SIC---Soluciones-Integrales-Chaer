import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { AccountSidebar } from "@/components/account-sidebar";
import { isApplicationAuthConfigured } from "@/lib/auth-config";

export default async function AccountLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const configured = isApplicationAuthConfigured();
  const session = configured ? await auth() : null;
  if (configured && !session?.user) redirect("/ingresar");
  if (configured && session?.user && !session.user.roles.includes("CLIENT")) redirect("/onboarding/rol");
  return <main className="account-shell"><AccountSidebar /><section className="account-main">{children}</section></main>;
}
