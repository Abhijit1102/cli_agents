import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

const handlerObj = toNextJsHandler(auth.handler);

export const GET = async (req: Request) => {
  const session = await auth.api.getSession({
    headers: req.headers, 
  });

  if (!session) {
    return Response.json({ error: "Not authenticated" }, { status: 401 });
  }

  return Response.json({
    id: session.user.id,
    email: session.user.email,
    name: session.user.name,
  });
};
