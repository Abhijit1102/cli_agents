import { auth } from "@/lib/auth";
import { toNextJsRequest, toNextJsResponse } from "better-auth/nextjs";

export async function GET(req: Request) {
  const session = await auth.api.getSession({
    headers: req.headers,
  });

  if (!session) {
    return Response.json({ error: "No active session" }, { status: 401 });
  }

  return Response.json(session);
}
