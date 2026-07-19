const apiUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8001";

export async function POST(request: Request) {
  const incoming = new URL(request.url);
  const resourceId = incoming.searchParams.get("data.id");
  const target = new URL("/v1/webhooks/mercado-pago", apiUrl);
  if (resourceId) target.searchParams.set("data.id", resourceId);
  try {
    const response = await fetch(target, {
      method: "POST",
      headers: {
        "content-type": request.headers.get("content-type") ?? "application/json",
        "x-signature": request.headers.get("x-signature") ?? "",
        "x-request-id": request.headers.get("x-request-id") ?? "",
      },
      body: await request.arrayBuffer(),
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    return new Response(await response.arrayBuffer(), { status: response.status, headers: { "content-type": response.headers.get("content-type") ?? "application/json", "cache-control": "no-store" } });
  } catch {
    return Response.json({ detail: "Billing webhook service unavailable" }, { status: 503 });
  }
}
