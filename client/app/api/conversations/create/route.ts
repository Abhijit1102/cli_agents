import { NextRequest } from "next/server";
import  prisma  from "@/lib/prisma";

export async function POST(req: NextRequest) {
  try {
    const { userId, mode = "chat", title = null } = await req.json();

    if (!userId) {
      return Response.json({ error: "userId required" }, { status: 400 });
    }

    const conversation = await prisma.conversation.create({
      data: {
        userId,
        mode,
        title: title || `New ${mode} conversation`,
      },
    });

    return Response.json(conversation);
  } catch (err) {
    console.error("Create conversation error:", err);
    return Response.json({ error: "Server error" }, { status: 500 });
  }
}
