"use server";

import { auth } from "@/auth";
import { sendConversationMessage } from "@/lib/internal-api";

export type MessageActionState = { error: string | null; sent: number };

export async function sendMessageAction(previous: MessageActionState, formData: FormData): Promise<MessageActionState> {
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId) return { error: "Tu sesión no es válida.", sent: previous.sent };
  const requestId = String(formData.get("request_id") ?? "");
  const body = String(formData.get("body") ?? "").trim();
  if (!/^[0-9a-f-]{36}$/i.test(requestId) || !body || body.length > 2000) return { error: "Escribí un mensaje de hasta 2.000 caracteres.", sent: previous.sent };
  try {
    await sendConversationMessage({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId, requestId, body });
    return { error: null, sent: previous.sent + 1 };
  } catch (error) {
    return { error: error instanceof Error ? error.message : "No pudimos enviar el mensaje.", sent: previous.sent };
  }
}
