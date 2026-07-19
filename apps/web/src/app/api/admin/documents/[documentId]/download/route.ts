import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { getAdminDocumentDownload } from "@/lib/internal-api";

export async function GET(request: Request, { params }: { params: Promise<{ documentId: string }> }) {
  const session = await auth();
  const roles = session?.user?.roles ?? [];
  if (!session?.user?.id || (!roles.includes("ADMIN") && !roles.includes("DOCUMENT_REVIEWER"))) return NextResponse.redirect(new URL("/ingresar", request.url));
  try {
    const { documentId } = await params;
    const download = await getAdminDocumentDownload({ userId: session.user.id, roles, sessionId: session.internalSessionId, documentId });
    return NextResponse.redirect(download.url);
  } catch {
    return NextResponse.redirect(new URL("/admin/documentos?error=download", request.url));
  }
}
