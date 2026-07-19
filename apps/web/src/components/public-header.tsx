import Link from "next/link";

export function PublicBrand() {
  return <Link className="brand" href="/" aria-label="SIC, inicio"><span className="brand-mark">S<span>Í</span>C</span><span>Soluciones Integrales Chaer</span></Link>;
}

export function PublicHeader() {
  return (
    <header className="site-header public-site-header">
      <PublicBrand />
      <nav aria-label="Navegación principal">
        <Link href="/servicios">Explorar servicios</Link>
        <Link href="/#como-funciona">¿Cómo funciona?</Link>
        <Link href="/onboarding/prestador">Ofrecer mis servicios</Link>
      </nav>
      <div className="header-actions"><Link className="primary small" href="/ingresar">Ingresar</Link></div>
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer>
      <PublicBrand />
      <p>Marketplace de servicios presenciales y remotos.</p>
      <div className="footer-links"><Link href="/privacidad">Privacidad</Link><Link href="/terminos">Términos</Link></div>
      <small>© 2026 SIC</small>
    </footer>
  );
}
