"use client";

import { useActionState, useState } from "react";
import Link from "next/link";

import { saveRoles, type RoleActionState } from "./actions";

const initialState: RoleActionState = { error: null };

export function RoleSelector({ enabled, initialRoles }: { enabled: boolean; initialRoles: string[] }) {
  const [roles, setRoles] = useState(() => new Set(initialRoles.length ? initialRoles : ["CLIENT"]));
  const [state, action, pending] = useActionState(saveRoles, initialState);

  function toggle(role: string) {
    setRoles((current) => {
      const next = new Set(current);
      if (next.has(role)) next.delete(role); else next.add(role);
      return next;
    });
  }

  return (
    <form action={action}>
      {[...roles].map((role) => <input key={role} type="hidden" name="roles" value={role} />)}
      <div className="role-grid">
        <button className={`role-card ${roles.has("CLIENT") ? "selected" : ""}`} type="button" aria-pressed={roles.has("CLIENT")} onClick={() => toggle("CLIENT")}>
          <span className="role-check">{roles.has("CLIENT") ? "✓" : "○"}</span><span className="role-icon">⌂</span>
          <span className="role-title">Quiero contratar servicios</span><span className="role-description">Buscá profesionales, guardá favoritos y gestioná tus contrataciones.</span>
          <span className="role-list"><i>Encontrar servicios cerca tuyo</i><i>Solicitar presupuestos privados</i><i>Calificar trabajos completados</i></span>
        </button>
        <button className={`role-card ${roles.has("PROVIDER") ? "selected" : ""}`} type="button" aria-pressed={roles.has("PROVIDER")} onClick={() => toggle("PROVIDER")}>
          <span className="role-check">{roles.has("PROVIDER") ? "✓" : "○"}</span><span className="role-icon">⚒</span>
          <span className="role-title">Quiero ofrecer mis servicios</span><span className="role-description">Creá tu perfil profesional, configurá tu cobertura y recibí clientes.</span>
          <span className="role-list"><i>Publicar varias aptitudes</i><i>Administrar disponibilidad</i><i>Construir reputación verificada</i></span>
        </button>
      </div>
      {state.error && <p className="form-error" role="alert">{state.error}</p>}
      <div className="role-actions"><Link href="/" className="secondary">Volver</Link><button className="primary" disabled={!enabled || !roles.size || pending}>{pending ? "Guardando…" : "Guardar y continuar"}</button></div>
    </form>
  );
}
