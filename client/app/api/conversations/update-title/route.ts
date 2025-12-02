import { NextRequest } from "next/server";
import  prisma  from "@/lib/prisma";

export async function PATCH(req: NextRequest) {
  try {
    const { conversationId, title } = await req.json();

    if (!conversationId || !title) {
      return Response.json({ error: "Missing fields" }, { status: 400 });
    }

    const updated = await prisma.conversation.update({
      where: { id: conversationId },
      data: { title },
    });

    return Response.json(updated);
  } catch (err) {
    console.error(err);
    return Response.json({ error: "Server error" }, { status: 500 });
  }
}
