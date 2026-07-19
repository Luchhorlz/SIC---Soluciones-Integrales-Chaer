import Link from "next/link";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { isApplicationAuthConfigured } from "@/lib/auth-config";

import { RoleSelector } from "./role-selector";

export const metadata = { title: "Elegí cómo usar SIC" };

export default async function RoleOnboardingPage() {
  const authReady = isApplicationAuthConfigured();
  const session = authReady ? await auth() : null;
  if (authReady && !session?.user) redirect("/ingresar");

  return (
    <main className="onboarding-shell">
      <header className="onboarding-header">
        <Link className="brand" href="/"><span className="brand-mark">S<span>Í</span>C</span><span>Soluciones Integrales Chaer</span></Link>
        <div className="onboarding-progress"><span className="active">1</span><i></i><span>2</span><i></i><span>3</span></div>
        <Link className="exit-link" href="/">Salir</Link>
      </header>
      <section className="role-step">
        <p className="eyebrow">PASO 1 DE 3</p>
        <h1>¿Cómo querés usar SIC?</h1>
        <p className="lead">Podés elegir las dos opciones y cambiarlo más adelante.</p>
        {!authReady && <div className="preview-notice">Vista previa del onboarding. El guardado se habilitará al configurar la autenticación y PostgreSQL.</div>}
        {session?.isDemo && <div className="preview-notice">Esta cuenta demo ya tiene un rol fijo. Ingresá con otro usuario demo para recorrer un panel diferente.</div>}
        <RoleSelector enabled={authReady && !session?.isDemo} initialRoles={session?.user.roles ?? []} />
        <p className="role-help">¿Necesitás ayuda? <a href="mailto:soporte@sic.local">Contactanos</a></p>
      </section>
    </main>
  );
}
