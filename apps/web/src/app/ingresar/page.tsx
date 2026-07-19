import Link from "next/link";

import { auth } from "@/auth";
import { isApplicationAuthConfigured, isDemoMode, isGoogleAuthConfigured } from "@/lib/auth-config";
import { demoAccounts } from "@/lib/demo-accounts";

import { signInWithDemo, signInWithGoogle, signOutFromSic } from "./actions";

export const metadata = {
  title: "Ingresar | SIC",
};

export default async function SignInPage({ searchParams }: { searchParams: Promise<{ demo_error?: string }> }) {
  const googleReady = isGoogleAuthConfigured();
  const demoReady = isDemoMode();
  const session = isApplicationAuthConfigured() ? await auth() : null;
  const params = await searchParams;

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
            {session?.user ? "Tu sesión ya está activa. Podés continuar con la configuración de tu cuenta." : demoReady && !googleReady ? "Mientras Google queda pendiente, podés recorrer SIC con uno de los accesos demo." : "Usamos Google para que tu identidad y tu sesión estén protegidas."}
          </p>

          {session?.user ? (
            <div className="active-session-card"><span>{session.isDemo ? "DEMO" : "SESIÓN ACTIVA"}</span><b>{session.user.name}</b><p>{session.user.roles.join(" · ")}</p><div><Link className="primary" href={session.user.roles.includes("ADMIN") ? "/admin/catalogo" : session.user.roles.includes("PROVIDER") ? "/prestador/panel" : "/cuenta"}>Continuar</Link><form action={signOutFromSic}><button className="secondary">Cambiar usuario</button></form></div></div>
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

          {demoReady && !session?.user && <section className="demo-login-section" aria-labelledby="demo-login-title"><div className="auth-divider"><span id="demo-login-title">Accesos de demostración</span></div>{params.demo_error && <div className="form-error">El usuario o la contraseña demo no coinciden.</div>}<div className="demo-account-grid">{demoAccounts.map((account) => <article key={account.username}><span>{account.username === "admin" ? "▦" : account.username === "cliente" ? "⌂" : "⚒"}</span><div><b>{account.username === "servicio" ? "Prestador" : account.username[0].toUpperCase() + account.username.slice(1)}</b><p>{account.description}</p><code>{account.username} / {account.password}</code></div><form action={signInWithDemo}><input type="hidden" name="username" value={account.username} /><input type="hidden" name="password" value={account.password} /><button type="submit" aria-label={`Ingresar como ${account.username}`}>Ingresar →</button></form></article>)}</div><p className="demo-security-note">Estas cuentas sólo existen con <code>DEMO_MODE</code> fuera de producción.</p></section>}

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
