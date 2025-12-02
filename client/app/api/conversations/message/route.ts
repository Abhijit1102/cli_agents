import { NextRequest } from "next/server";
import  prisma  from "@/lib/prisma";

export async function POST(req: NextRequest) {
  try {
    const { conversationId, role, content } = await req.json();

    if (!conversationId || !role || !content) {
      return Response.json({ error: "Missing fields" }, { status: 400 });
    }

    const contentStr =
      typeof content === "string" ? content : JSON.stringify(content);

    const message = await prisma.message.create({
      data: {
        conversationId,
        role,
        content: contentStr,
      },
    });

    return Response.json(message);
  } catch (err) {
    console.error("Add message error:", err);
    return Response.json({ error: "Server error" }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  try {
    const conversationId = req.nextUrl.searchParams.get("conversationId");

    if (!conversationId) {
      return Response.json(
        { error: "conversationId required" },
        { status: 400 }
      );
    }

    const messages = await prisma.message.findMany({
      where: { conversationId },
      orderBy: { createdAt: "asc" },
    });

    const formatted = messages.map((msg) => ({
      ...msg,
      content: safeParse(msg.content),
    }));

    return Response.json(formatted);
  } catch (err) {
    console.error(err);
    return Response.json({ error: "Server error" }, { status: 500 });
  }
}

function safeParse(str: string) {
  try {
    return JSON.parse(str);
  } catch {
    return str;
  }
}

