import { NextRequest } from "next/server";
import  prisma  from "@/lib/prisma";

export async function DELETE(req: NextRequest) {
  try {
    const { conversationId, userId } = await req.json();

    if (!conversationId || !userId) {
      return Response.json({ error: "Missing fields" }, { status: 400 });
    }

    const deleted = await prisma.conversation.deleteMany({
      where: { id: conversationId, userId },
    });

    return Response.json(deleted);
  } catch (err) {
    console.error(err);
    return Response.json({ error: "Server error" }, { status: 500 });
  }
}
