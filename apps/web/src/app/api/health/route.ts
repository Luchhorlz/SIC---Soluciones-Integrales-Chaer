import { NextResponse } from "next/server";

export async function GET() {
  const apiUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8001";
  try {
    const response = await fetch(`${apiUrl}/health/ready`, { cache: "no-store", signal: AbortSignal.timeout(2000) });
    const payload: unknown = await response.json();
    return NextResponse.json({ bff: "ok", api: payload }, { status: response.ok ? 200 : 503 });
  } catch {
    return NextResponse.json({ bff: "ok", api: { status: "unavailable" } }, { status: 503 });
  }
}
