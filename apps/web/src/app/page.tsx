import Link from "next/link";

const categories = [
  ["⌂", "Hogar y mantenimiento"],
  ["✦", "Limpieza"],
  ["ϟ", "Electricidad"],
  ["♒", "Plomería"],
  ["▰", "Pintura"],
  ["⌘", "Informática"],
  ["◇", "Automotor"],
  ["○", "Clases"],
];

const providers = [
  ["CP", "Carlos Pereyra", "Plomería", "4.9", "1,2 km"],
  ["LG", "Laura Gómez", "Limpieza", "4.8", "1,8 km"],
  ["MV", "Martín Vega", "Electricidad", "4.9", "2,3 km"],
  ["JN", "Javier Núñez", "Hogar y mantenimiento", "4.8", "2,7 km"],
];

export default function Home() {
  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#inicio" aria-label="SIC, inicio">
          <span className="brand-mark">S<span>Í</span>C</span>
          <span>Soluciones Integrales Chaer</span>
        </a>
        <nav aria-label="Navegación principal">
          <a className="active" href="#servicios">Explorar servicios</a>
          <a href="#como-funciona">¿Cómo funciona?</a>
          <a href="#prestadores">Ofrecer mis servicios</a>
        </nav>
        <div className="header-actions">
          <button className="icon-button" aria-label="Notificaciones">♢</button>
          <Link className="primary small" href="/ingresar">Ingresar</Link>
        </div>
      </header>

      <section className="hero" id="inicio">
        <div className="hero-copy">
          <p className="eyebrow">SERVICIOS CONFIABLES, CUANDO LOS NECESITÁS</p>
          <h1>Encontrá el servicio que necesitás, <span>cerca tuyo o a distancia</span></h1>
          <p className="lead">Profesionales verificados listos para ayudarte.</p>
          <form className="search" action="#servicios">
            <label>
              <span aria-hidden="true">⌕</span>
              <input aria-label="Servicio" placeholder="¿Qué servicio necesitás?" />
            </label>
            <label>
              <span aria-hidden="true">⌖</span>
              <input aria-label="Ubicación" defaultValue="Moreno, Buenos Aires" />
            </label>
            <button className="primary" type="submit">Buscar</button>
          </form>
          <div className="trust-row">
            <div><b>✓ Prestadores verificados</b><span>Seguridad y confianza</span></div>
            <div><b>☆ Calificaciones reales</b><span>Opiniones verificadas</span></div>
            <div><b>◷ Atención cercana</b><span>Seguimiento en cada paso</span></div>
          </div>
        </div>
        <div className="hero-visual" aria-label="Personas conectadas con profesionales">
          <div className="orbit orbit-one">⚒</div>
          <div className="orbit orbit-two">♧</div>
          <div className="orbit orbit-three">▦</div>
          <div className="person worker"><span>CP</span></div>
          <div className="person client"><span>LG</span></div>
          <div className="visual-caption">Soluciones presenciales y remotas</div>
        </div>
      </section>

      <section className="section" id="servicios">
        <div className="section-heading"><div><p className="eyebrow">EXPLORÁ SIC</p><h2>Categorías destacadas</h2></div><a href="#servicios">Ver todas →</a></div>
        <div className="category-grid">
          {categories.map(([icon, name]) => <a className="category-card" href="#prestadores" key={name}><span>{icon}</span><b>{name}</b></a>)}
        </div>
      </section>

      <section className="section providers" id="prestadores">
        <div className="section-heading"><div><p className="eyebrow">CERCA TUYO</p><h2>Prestadores destacados</h2></div><a href="#prestadores">Ver todos →</a></div>
        <div className="provider-grid">
          {providers.map(([initials, name, service, rating, distance]) => (
            <article className="provider-card" key={name}>
              <div className="avatar">{initials}</div>
              <div><h3>{name}</h3><p>{service}</p><b><span className="star">★</span> {rating}</b><span className="distance">⌖ A {distance}</span></div>
            </article>
          ))}
        </div>
      </section>

      <section className="coming" id="como-funciona">
        <div><p className="eyebrow">PRIMERA VERSIÓN NAVEGABLE</p><h2>La base de SIC ya está en marcha.</h2><p>Esta portada permite validar el lenguaje visual mientras construimos búsqueda, perfiles y contratación por fases.</p></div>
        <Link className="secondary" href="/ingresar">Quiero ofrecer servicios</Link>
      </section>

      <footer><div className="brand footer-brand"><span className="brand-mark">S<span>Í</span>C</span><span>Soluciones Integrales Chaer</span></div><p>Marketplace de servicios presenciales y remotos.</p><small>© 2026 SIC</small></footer>
    </main>
  );
}
