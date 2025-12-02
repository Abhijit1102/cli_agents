import { NextRequest, NextResponse } from "next/server";
import { AIService, AIMessage } from "@/lib/aiService";

export async function POST(req: NextRequest) {
  try {
    const { messages } = (await req.json()) as { messages: AIMessage[] };

    const ai = new AIService();
    const response = await ai.getResponse(messages);

    return NextResponse.json({ text: response });
  } catch (err) {
    return NextResponse.json({ error: (err as Error).message }, { status: 500 });
  }
}
