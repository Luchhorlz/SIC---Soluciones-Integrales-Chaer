import Link from "next/link";
import { redirect } from "next/navigation";

import { auth } from "@/auth";

export const metadata = { title: "Mi cuenta | SIC" };

export default async function AccountPage() {
  const configured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET);
  const session = configured ? await auth() : null;
  if (configured && !session?.user) redirect("/ingresar");

  return <main className="account-shell">
    <aside className="account-sidebar"><Link className="brand" href="/"><span className="brand-mark">S<span>Í</span>C</span><span>Soluciones Integrales Chaer</span></Link><nav><a className="active" href="#resumen">⌂ Inicio</a><a href="#contrataciones">▣ Mis contrataciones</a><a href="#favoritos">♡ Favoritos</a><a href="#direcciones">⌖ Direcciones</a><a href="#configuracion">⚙ Configuración</a></nav></aside>
    <section className="account-main"><div className="account-top"><div><p className="eyebrow">MI CUENTA SIC</p><h1>{session?.user?.name ? `Hola, ${session.user.name}` : "Panel del cliente"}</h1><p>Tu espacio para gestionar servicios, favoritos y direcciones.</p></div><Link className="primary small" href="/#servicios">Explorar servicios</Link></div>
      {!configured && <div className="preview-notice account-preview">Vista previa del panel. Los datos reales aparecerán después del ingreso con Google.</div>}
      <div className="account-stats"><article><span>▣</span><div><b>0</b><p>Contrataciones activas</p></div></article><article><span>◷</span><div><b>0</b><p>En progreso</p></div></article><article><span>✓</span><div><b>0</b><p>Completadas</p></div></article><article><span>♡</span><div><b>0</b><p>Prestadores favoritos</p></div></article></div>
      <div className="account-empty"><div>⌕</div><h2>Empezá a encontrar soluciones</h2><p>Todavía no tenés contrataciones. Explorá los servicios disponibles y elegí un prestador.</p><Link className="primary" href="/#servicios">Buscar servicios</Link></div>
    </section>
  </main>;
}
