import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { uploadProviderDocument } from "@/lib/internal-api";

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.id || !session.user.roles.includes("PROVIDER")) return NextResponse.redirect(new URL("/ingresar", request.url), 303);
  try {
    const contentLength = Number(request.headers.get("content-length") ?? 0);
    if (contentLength > 11 * 1024 * 1024) throw new Error("Upload too large");
    const formData = await request.formData();
    const file = formData.get("file");
    if (!(file instanceof File) || file.size === 0 || file.size > 10 * 1024 * 1024) throw new Error("Invalid private document size");
    await uploadProviderDocument({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId, formData });
    return NextResponse.redirect(new URL("/prestador/documentacion?status=uploaded", request.url), 303);
  } catch {
    return NextResponse.redirect(new URL("/prestador/documentacion?error=upload", request.url), 303);
  }
}
