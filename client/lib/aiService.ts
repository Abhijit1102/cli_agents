import { google } from "@ai-sdk/google";
import { streamText } from "ai";

export interface AIMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export class AIService {
  private model: ReturnType<typeof google>;
  private systemPrompt: string;

  constructor(
    modelName: string = process.env.AGENTIC_MODE || "gemini-2.5-flash",
    systemPrompt: string = `
    You are a helpful assistant. Respond in Markdown only.
    Do NOT include any HTML tags. Do NOT use emojis.
    Output should be plain text suitable for terminal display.`
  ) {
    if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
      throw new Error("Google API key missing in environment variable");
    }

    this.model = google(modelName as any);
    this.systemPrompt = systemPrompt;
  }

  async getResponse(messages: AIMessage[] = []): Promise<string> {
    if (messages.length === 0) throw new Error("Messages array cannot be empty");

    // Prepend system prompt to messages
    const promptMessages: AIMessage[] = [
      { role: "system", content: this.systemPrompt },
      ...messages,
    ];

    const result = streamText({
      model: this.model,
      messages: promptMessages,
    });

    let fullText = "";
    for await (const chunk of result.textStream) {
      fullText += chunk;
    }

    return fullText;
  }
}
