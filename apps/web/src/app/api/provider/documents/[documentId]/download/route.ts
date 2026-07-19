import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { getProviderDocumentDownload } from "@/lib/internal-api";

export async function GET(request: Request, { params }: { params: Promise<{ documentId: string }> }) {
  const session = await auth();
  if (!session?.user?.id || !session.user.roles.includes("PROVIDER")) return NextResponse.redirect(new URL("/ingresar", request.url));
  try {
    const { documentId } = await params;
    const download = await getProviderDocumentDownload({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId, documentId });
    return NextResponse.redirect(download.url);
  } catch {
    return NextResponse.redirect(new URL("/prestador/documentacion?error=download", request.url));
  }
}
