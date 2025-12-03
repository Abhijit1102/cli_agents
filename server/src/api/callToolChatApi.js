import axios from "axios";

// ---------------- Helper: Call API via Axios ----------------
export async function callToolChatAPI({ messages, tools, structured = false, schema = null, prompt = null }) {
  try {
    const res = await axios.post("http://localhost:3000/api/ai/tool_chat", {
      messages,
      tools,
      structured,
      schema,
      prompt
    }, {
      headers: { "Content-Type": "application/json" }
    });

    return res.data;
  } catch (err) {
    if (err.response) {
      throw new Error(`API Error: ${err.response.data.error || err.response.statusText}`);
    } else {
      throw new Error(`API Error: ${err.message}`);
    }
  }
}
