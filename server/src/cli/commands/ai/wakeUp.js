import logger from "../../../logger.js";
import { Command } from "commander";
import yoctoSpinner from "yocto-spinner";
import { getStoredToken } from "../../../core/token.js";
import { select } from "@clack/prompts";
import axios from "axios";
import { startChat } from "../../chat/chat-with-ai.js";
import { startToolChat } from "../../chat/chat-with-ai-toot.js";

async function fetchUserByToken(token) {
  try {
    const res = await axios.get(`http://localhost:3000/api/user`, {
      params: { token },
    });

    // logger.info("User:", res.data);
    return res.data;

  } catch (err) {
    logger.error("Error:", err.response?.data || err.message);
    return null;
  }
}

const wakeUpAction = async () => {
  const token = await getStoredToken();
  // console.log("token:", token.access_token);

  if (!token.access_token) {
    logger.error("Not Authenticated. Please Login");
    return;
  }

  const spinner = yoctoSpinner({
    text: "Fetching user information ...."
  });

  spinner.start();

  // FIXED: declare + await
  const user = await fetchUserByToken(token.access_token);

  spinner.stop();

  if (!user) {
    logger.error("User not found");
    return;
  }

  logger.success(`Welcome back, ${user.name}\n`);

  const choice = await select({
    message: "Select an Option:",
    options: [
      { value: "chat", label: "Chat", hint: "Simple chat with AI" },
      { value: "tool", label: "Tool Calling", hint: "Chat with tools (Google Search, Code Execution)" },
      { value: "agent", label: "Agentic Mode", hint: "Advanced AI agent (Coming soon...)" },
    ],
  });

  switch (choice) {
    case "chat":
      logger.info("Chat is selected.");
      startChat("chat")
      break;
    case "tool":
      logger.success("Tool calling is selected");
      startToolChat("tool")
      break;
    case "agent":
      logger.warn("Advanced AI agent is coming soon...");
      break;
  }
};

export const wakeUp = new Command("wakeup")
  .description("Wake up the AI")
  .action(wakeUpAction);
