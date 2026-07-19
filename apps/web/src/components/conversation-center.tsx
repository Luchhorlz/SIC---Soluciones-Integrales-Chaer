"use client";

import Link from "next/link";
import { useActionState, useEffect, useRef, useState } from "react";

import { sendMessageAction, type MessageActionState } from "@/app/message-actions";
import type { Conversation, ConversationSummary } from "@/lib/internal-api";

const initialState: MessageActionState = { error: null, sent: 0 };

export function ConversationCenter({ summaries, initial, selectedRequestId, basePath, enabled }: { summaries: ConversationSummary[]; initial: Conversation | null; selectedRequestId: string | null; basePath: string; enabled: boolean }) {
  const [conversation, setConversation] = useState(initial);
  const [state, action, pending] = useActionState(sendMessageAction, initialState);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (!selectedRequestId || !enabled) return;
    let active = true;
    const refresh = async () => {
      if (document.visibilityState !== "visible") return;
      try {
        const response = await fetch(`/api/messages/${selectedRequestId}`, { cache: "no-store" });
        if (response.ok && active) setConversation(await response.json() as Conversation);
      } catch { /* the current view remains available */ }
    };
    void refresh();
    const timer = window.setInterval(refresh, 8000);
    document.addEventListener("visibilitychange", refresh);
    return () => { active = false; window.clearInterval(timer); document.removeEventListener("visibilitychange", refresh); };
  }, [selectedRequestId, enabled, state.sent]);
  useEffect(() => { if (state.sent > 0) formRef.current?.reset(); }, [state.sent]);

  return <div className="messages-layout">
    <aside className="conversation-list"><header><h2>Conversaciones</h2><span>{summaries.length}</span></header>{summaries.length ? summaries.map((item) => <Link key={item.id} className={item.request_id === selectedRequestId ? "active" : ""} href={`${basePath}?request=${item.request_id}`}><div><b>{item.counterpart_name}</b><small>{item.service_name}</small></div>{item.unread_count > 0 && <span>{item.unread_count}</span>}<p>{item.last_message_preview ?? item.request_title}</p></Link>) : <div className="message-empty"><span>◇</span><p>Todavía no hay conversaciones privadas.</p></div>}</aside>
    <section className="conversation-thread">{conversation ? <><header><div><small>{conversation.conversation.service_name}</small><h2>{conversation.conversation.counterpart_name}</h2><p>{conversation.conversation.request_title}</p></div><span>{conversation.conversation.request_status}</span></header><div className="message-stream" aria-live="polite">{conversation.messages.length ? conversation.messages.map((message) => <article key={message.id} className={message.is_mine ? "mine" : "theirs"}><b>{message.is_mine ? "Vos" : message.sender_name}</b><p>{message.body}</p><time>{new Intl.DateTimeFormat("es-AR", { timeZone: "America/Argentina/Buenos_Aires", dateStyle: "short", timeStyle: "short" }).format(new Date(message.created_at))}</time></article>) : <div className="message-empty"><span>✦</span><h3>Iniciá la conversación</h3><p>Este chat existe únicamente dentro de la solicitud seleccionada.</p></div>}</div><form ref={formRef} className="message-composer" action={action}><input type="hidden" name="request_id" value={selectedRequestId ?? ""} /><label htmlFor="message-body">Mensaje privado</label><div><textarea id="message-body" name="body" required minLength={1} maxLength={2000} placeholder="Escribí un mensaje claro sobre este servicio…" disabled={!enabled || pending}></textarea><button className="primary" disabled={!enabled || pending}>{pending ? "Enviando…" : "Enviar"}</button></div>{state.error && <p className="form-error">{state.error}</p>}<small>Actualización automática cada 8 segundos mientras esta pestaña está visible.</small></form></> : <div className="message-empty thread-empty"><span>◇</span><h3>Elegí una conversación</h3><p>Los mensajes siempre están vinculados a una solicitud válida.</p></div>}</section>
  </div>;
}
