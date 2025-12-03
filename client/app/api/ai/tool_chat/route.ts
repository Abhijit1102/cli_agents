import { createGoogleGenerativeAI } from "@ai-sdk/google";
import { streamText, generateObject } from "ai";

const AI_CONFIG = {
  temperature: 0.7,
  maxTokens: 2000,
};

export async function POST(req: Request) {
  try {
    const { messages, tools, structured, schema, prompt } = await req.json();

    if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
      return new Response(
        JSON.stringify({ error: "GOOGLE_API_KEY missing in env" }),
        { status: 500 }
      );
    }

    // ✅ v2 correct setup
    const googleProvider = createGoogleGenerativeAI({
      apiKey: process.env.GOOGLE_API_KEY!,
    });

    // pick the model
    const model = googleProvider("gemini-2.5-flash");

    // ---------- Structured Output ---------- //
    if (structured && schema) {
      const result = await generateObject({
        model,
        schema,
        prompt,
      });

      return new Response(
        JSON.stringify({
          object: result.object,
          usage: result.usage,
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    // ---------- Streaming Chat + Tools ---------- //
    const streamConfig: any = {
      model,
      messages,
      temperature: AI_CONFIG.temperature,
      maxTokens: AI_CONFIG.maxTokens,
    };

    if (tools && Object.keys(tools).length > 0) {
      streamConfig.tools = tools;
      streamConfig.maxSteps = 5;
    }

    const result = streamText(streamConfig);

    let fullText = "";
    const toolCalls: any[] = [];
    const toolResults: any[] = [];

    for await (const chunk of result.textStream) {
      fullText += chunk;
    }

    const steps = await result.steps

    if (steps) {
      for (const step of steps) {
        if (step.toolCalls) toolCalls.push(...step.toolCalls);
        if (step.toolResults) toolResults.push(...step.toolResults);
      }
    }


    return new Response(
      JSON.stringify({
        content: fullText,
        finishReason: result.finishReason,
        usage: result.usage,
        toolCalls,
        toolResults,
        steps: result.steps,
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err?.message || "Unknown AI error" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
