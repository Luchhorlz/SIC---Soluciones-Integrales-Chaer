import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { getConversation } from "@/lib/internal-api";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ requestId: string }> }) {
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  try {
    const { requestId } = await context.params;
    const conversation = await getConversation({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId, requestId });
    return NextResponse.json(conversation, { headers: { "cache-control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Conversation unavailable" }, { status: 404 });
  }
}
