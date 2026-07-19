"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/cuenta", icon: "⌂", label: "Inicio", enabled: true },
  { href: "/cuenta/contrataciones", icon: "▣", label: "Mis contrataciones", enabled: true },
  { href: "/cuenta/mensajes", icon: "◇", label: "Mensajes", enabled: true },
  { href: "/cuenta/notificaciones", icon: "◉", label: "Notificaciones", enabled: true },
  { href: "/cuenta/favoritos", icon: "♡", label: "Favoritos", enabled: true },
  { href: "/cuenta/direcciones", icon: "⌖", label: "Direcciones", enabled: true },
  { href: "/cuenta/configuracion", icon: "⚙", label: "Configuración", enabled: false },
];

export function AccountSidebar() {
  const pathname = usePathname();

  return (
    <aside className="account-sidebar">
      <Link className="brand" href="/">
        <span className="brand-mark">S<span>Í</span>C</span>
        <span>Soluciones Integrales Chaer</span>
      </Link>
      <nav>
        {items.map((item) => item.enabled ? (
          <Link key={item.href} className={pathname === item.href ? "active" : ""} href={item.href}>
            {item.icon} {item.label}
          </Link>
        ) : (
          <span key={item.href} aria-disabled="true" title="Disponible en una próxima etapa">
            {item.icon} {item.label}
          </span>
        ))}
      </nav>
      <div className="sidebar-help">
        <b>¿Necesitás ayuda?</b>
        <p>Estamos para acompañarte.</p>
        <button disabled>Contactar soporte</button>
      </div>
    </aside>
  );
}
