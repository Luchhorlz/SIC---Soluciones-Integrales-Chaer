import Link from "next/link";
import { redirect } from "next/navigation";

import { auth } from "@/auth";

import { RoleSelector } from "./role-selector";

export const metadata = { title: "Elegí cómo usar SIC" };

export default async function RoleOnboardingPage() {
  const googleReady = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET);
  const session = googleReady ? await auth() : null;
  if (googleReady && !session?.user) redirect("/ingresar");

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
        {!googleReady && <div className="preview-notice">Vista previa del onboarding. El guardado se habilitará al conectar Google y PostgreSQL.</div>}
        <RoleSelector enabled={googleReady} initialRoles={session?.user.roles ?? []} />
        <p className="role-help">¿Necesitás ayuda? <a href="mailto:soporte@sic.local">Contactanos</a></p>
      </section>
    </main>
  );
}
