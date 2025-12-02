import { NextRequest } from "next/server";
import  prisma  from "@/lib/prisma";
import { ConversationMode } from "@/lib/generated/prisma/enums";

export async function GET(req: NextRequest) {
  try {
    const userId = req.nextUrl.searchParams.get("userId");
    const conversationId = req.nextUrl.searchParams.get("conversationId");

    const modeParam = req.nextUrl.searchParams.get("mode") as ConversationMode | null;
    const mode: ConversationMode =
      modeParam && ["chat", "tool", "agent"].includes(modeParam)
        ? modeParam
        : "chat";

    if (!userId) {
      return Response.json({ error: "userId required" }, { status: 400 });
    }

    // If conversationId provided → fetch that conversation
    if (conversationId) {
      const conversation = await prisma.conversation.findFirst({
        where: { id: conversationId, userId },
        include: {
          messages: {
            orderBy: { createdAt: "asc" },
          },
        },
      });

      if (conversation) {
        return Response.json(conversation);
      }
    }

    // Else create new conversation
    const newConversation = await prisma.conversation.create({
      data: {
        userId,
        mode,
        title: `New ${mode} conversation`,
      },
      include: {
        messages: true,
      },
    });

    return Response.json(newConversation);
  } catch (err) {
    console.error(err);
    return Response.json({ error: "Server error" }, { status: 500 });
  }
}
