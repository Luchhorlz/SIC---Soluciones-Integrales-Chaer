import Link from "next/link";
import type { ReactNode } from "react";

type ProviderShellProps = {
  active: "panel" | "profile" | "services" | "documents";
  displayName?: string | null;
  children: ReactNode;
};

const links = [
  { key: "panel", href: "/prestador/panel", icon: "⌂", label: "Inicio" },
  { key: "profile", href: "/prestador/perfil", icon: "♙", label: "Mi perfil" },
  { key: "services", href: "/prestador/servicios", icon: "▣", label: "Mis servicios" },
  { key: "documents", href: "/prestador/documentacion", icon: "▤", label: "Documentación" },
] as const;

export function ProviderShell({ active, displayName, children }: ProviderShellProps) {
  return (
    <main className="provider-shell">
      <aside className="provider-sidebar">
        <Link className="brand" href="/"><span className="brand-mark">S<span>Í</span>C</span><span>Soluciones Integrales Chaer</span></Link>
        <nav aria-label="Panel del prestador">
          {links.map((item) => <Link key={item.key} className={active === item.key ? "active" : ""} href={item.href}><span>{item.icon}</span>{item.label}</Link>)}
          <span><i>▤</i>Contrataciones <small>Próximamente</small></span>
          <span><i>◇</i>Suscripción <small>Fase 7</small></span>
        </nav>
        <div className="provider-sidebar-help"><span>?</span><b>¿Necesitás ayuda?</b><p>Tu configuración se guarda de forma privada.</p></div>
      </aside>
      <section className="provider-main">
        <header className="provider-topbar"><div><span>Panel de prestador</span><small>Configuración privada de tu oferta</small></div><div className="provider-user"><span>{displayName?.slice(0, 1).toUpperCase() || "S"}</span><div><b>{displayName || "Vista previa"}</b><small>Prestador</small></div></div></header>
        {children}
      </section>
    </main>
  );
}
