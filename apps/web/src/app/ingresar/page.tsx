import Link from "next/link";

import { auth } from "@/auth";

import { signInWithGoogle } from "./actions";

export const metadata = {
  title: "Ingresar | SIC",
};

export default async function SignInPage() {
  const googleReady = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET);
  const session = googleReady ? await auth() : null;

  return (
    <main className="auth-shell">
      <section className="auth-brand-panel">
        <Link className="brand brand-light" href="/" aria-label="Volver al inicio de SIC">
          <span className="brand-mark">S<span>Í</span>C</span>
          <span>Soluciones Integrales Chaer</span>
        </Link>
        <div className="auth-promise">
          <p className="eyebrow">UN SOLO INGRESO, DOS FORMAS DE USAR SIC</p>
          <h1>Conectá con soluciones. Ofrecé lo que sabés hacer.</h1>
          <p>Tu misma cuenta puede contratar servicios y también activar un perfil profesional.</p>
          <ul>
            <li><span>✓</span> Perfiles y opiniones verificadas</li>
            <li><span>✓</span> Solicitudes privadas y seguras</li>
            <li><span>✓</span> Control total sobre tus roles</li>
          </ul>
        </div>
        <p className="auth-legal">SIC nunca publica búsquedas abiertas en tu nombre.</p>
      </section>

      <section className="auth-form-panel">
        <div className="auth-card">
          <Link className="back-link" href="/">← Volver al inicio</Link>
          <p className="eyebrow">BIENVENIDO A SIC</p>
          <h2>{session?.user ? `Hola, ${session.user.name ?? "bienvenido"}` : "Ingresá a tu cuenta"}</h2>
          <p className="auth-intro">
            {session?.user ? "Tu sesión ya está activa. Podés continuar con la configuración de tu cuenta." : "Usamos Google para que tu identidad y tu sesión estén protegidas."}
          </p>

          {session?.user ? (
            <Link className="primary auth-primary" href="/onboarding/rol">Continuar</Link>
          ) : googleReady ? (
            <form action={signInWithGoogle}>
              <button className="google-button" type="submit"><span>G</span> Continuar con Google</button>
            </form>
          ) : (
            <div className="auth-pending" role="status">
              <span>◷</span>
              <div><b>Ingreso en preparación</b><p>La interfaz ya está lista. Falta conectar las credenciales privadas de Google para habilitar el acceso real.</p></div>
            </div>
          )}

          <div className="auth-divider"><span>Tu cuenta SIC</span></div>
          <div className="auth-benefits">
            <div><span>⌂</span><b>Como cliente</b><p>Buscá y contratá profesionales.</p></div>
            <div><span>✦</span><b>Como prestador</b><p>Publicá tus aptitudes y recibí solicitudes.</p></div>
          </div>
          <p className="auth-terms">Al continuar, aceptás los <Link href="/terminos">Términos</Link> y la <Link href="/privacidad">Política de privacidad</Link> de SIC.</p>
        </div>
      </section>
    </main>
  );
}
