import axios from "axios";

export async function getAIResponseFromAPI(messages) {
  try {
    const res = await axios.post("http://localhost:3000/api/ai/chat", { messages });
    return res.data.text;
  } catch (err) {
    console.error("Failed to get AI response from API:", err.response?.data?.error || err.message);
    throw err;
  }
}
