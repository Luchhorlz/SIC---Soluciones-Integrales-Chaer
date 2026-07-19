import { auth } from "@/auth";
import { ConversationCenter } from "@/components/conversation-center";
import { isApplicationAuthConfigured } from "@/lib/auth-config";
import { getConversation, getConversations, type Conversation, type ConversationSummary } from "@/lib/internal-api";

export const dynamic = "force-dynamic";
export const metadata = { title: "Mensajes privados | SIC" };

export default async function ClientMessagesPage({ searchParams }: { searchParams: Promise<{ request?: string }> }) {
  const configured = isApplicationAuthConfigured();
  const session = configured ? await auth() : null; const query = await searchParams;
  let summaries: ConversationSummary[] = []; let conversation: Conversation | null = null; let unavailable = false;
  if (session?.user?.roles.includes("CLIENT")) {
    const input = { userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId };
    try { summaries = await getConversations(input); const selected = query.request ?? summaries[0]?.request_id; if (selected) conversation = await getConversation({ ...input, requestId: selected }); } catch { unavailable = true; }
  }
  const selected = query.request ?? conversation?.conversation.request_id ?? null;
  return <><div className="account-top"><div><p className="eyebrow">MENSAJERÍA CONTEXTUAL</p><h1>Mensajes</h1><p>Conversaciones privadas vinculadas a tus solicitudes y contrataciones.</p></div></div>{!configured && <div className="preview-notice account-preview">Vista previa: el chat real requiere autenticación y PostgreSQL.</div>}{unavailable && <div className="form-error account-preview">No pudimos cargar tus conversaciones.</div>}<ConversationCenter key={selected ?? "empty"} summaries={summaries} initial={conversation} selectedRequestId={selected} basePath="/cuenta/mensajes" enabled={Boolean(session?.user && !unavailable)} /></>;
}
