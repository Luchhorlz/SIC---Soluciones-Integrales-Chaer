import { ConversationCenter } from "@/components/conversation-center";
import { ProviderShell } from "@/components/provider-shell";
import { getConversation, getConversations, type Conversation, type ConversationSummary } from "@/lib/internal-api";
import { providerPageContext } from "@/lib/provider-page";

export const dynamic = "force-dynamic";
export const metadata = { title: "Mensajes de clientes | SIC" };

export default async function ProviderMessagesPage({ searchParams }: { searchParams: Promise<{ request?: string }> }) {
  const context = await providerPageContext({ requireProfile: true }); const query = await searchParams;
  let summaries: ConversationSummary[] = []; let conversation: Conversation | null = null; let unavailable = context.apiUnavailable;
  if (context.input && context.profile && !unavailable) { try { summaries = await getConversations(context.input); const selected = query.request ?? summaries[0]?.request_id; if (selected) conversation = await getConversation({ ...context.input, requestId: selected }); } catch { unavailable = true; } }
  const selected = query.request ?? conversation?.conversation.request_id ?? null;
  return <ProviderShell active="messages" displayName={context.profile?.display_name}><div className="provider-page-heading"><div><p className="eyebrow">MENSAJERÍA CONTEXTUAL</p><h1>Mensajes</h1><p>Respondé sólo dentro de solicitudes legítimas dirigidas a tu perfil.</p></div></div>{!context.configured && <div className="preview-notice provider-page-notice">Vista previa: el chat real requiere autenticación y PostgreSQL.</div>}{unavailable && context.configured && <div className="form-error provider-page-notice">No pudimos cargar las conversaciones.</div>}<div className="provider-message-wrapper"><ConversationCenter key={selected ?? "empty"} summaries={summaries} initial={conversation} selectedRequestId={selected} basePath="/prestador/mensajes" enabled={Boolean(context.input && !unavailable)} /></div></ProviderShell>;
}
