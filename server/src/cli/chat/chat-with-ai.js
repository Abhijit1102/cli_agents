import { text, isCancel, cancel, intro, outro } from "@clack/prompts";
import logger from "../../logger.js"
import yoctoSpinner from "yocto-spinner";
import chalk from "chalk";
import boxen from "boxen";

import {ChatService} from "../../service/chat-sevice.js"

import { getStoredToken } from "../../core/token.js"
import {getMe} from "../../api/user.api.js"
import { getAIResponseFromAPI } from "../../api/getAIreply.js"

import { marked } from "marked";
import { markedTerminal } from "marked-terminal";


// Configure marked to use terminal renderer
marked.use(
  markedTerminal({
    // Styling options for terminal output
    code: chalk.cyan,
    blockquote: chalk.gray.italic,
    heading: chalk.green.bold,
    firstHeading: chalk.magenta.underline.bold,
    hr: chalk.reset,
    listitem: chalk.reset,
    list: chalk.reset,
    paragraph: chalk.reset,
    strong: chalk.bold,
    em: chalk.italic,
    codespan: chalk.yellow.bgBlack,
    del: chalk.dim.gray.strikethrough,
    link: chalk.blue.underline,
    href: chalk.blue.underline,
  })
);

const chatService = new ChatService();

async function getUserFromToken() {
  const token = await getStoredToken();
  // console.log("token:", token);

  if (!token?.access_token) {
    throw new Error("Not Authenticated. Please run 'agents login' first");
  }

  const spinner = yoctoSpinner({ text: "Authenticating..." }).start();

  const user = await getMe(token); // ✅ pass token here

  if (!user) {
    spinner.error("User not found");
    throw new Error("User not found. Please login again");
  }

  spinner.success(`Welcome back, ${user.name}`);

  return user;
}

async function initConversation(userId, conversationId=null, mode="chat"){
  const spinner = yoctoSpinner({
    text: "Loading coversation..."
  }).start();

  const conversation = await chatService.getOrCreateConversation(
    userId,
    conversationId,
    mode
  )

  spinner.success("Conversation Loaded!..")

  logger.conversationInfo({
    id: conversation.id,
    title: conversation.title,
    mode: conversation.mode,
  });

  if(conversation.messages?.length > 0) {
    logger.conversationMessages(conversation.messages);
  }

  return conversation;

}

async function  saveMessage(conversationId, role, content) {
  return await chatService.addMessage(conversationId, role, content)
}

async function getAIResponse(conversationId) {
  const spinner = yoctoSpinner({ 
    text: "AI is thinking...",
    color: "cyan"
  }).start();

  const dbMessages = await chatService.getMessages(conversationId);
  const aiMessages = chatService.formatMessagesForAI(dbMessages);

  try {
    // Stop thinking spinner
    spinner.stop();

    // Print assistant header
    console.log("\n");
    console.log(chalk.green.bold("🤖 Assistant:"));
    console.log(chalk.gray("─".repeat(60)));

    // Show response spinner
    const responseSpinner = yoctoSpinner({
      text: "✨ AI is responding..."
    }).start();

    // Call Next.js API to get full AI response
    const fullResponse = await getAIResponseFromAPI(aiMessages);

    // Stop "AI is responding..." spinner
    responseSpinner.stop();

    // Render Markdown using your logger
    logger.markdown(fullResponse);

    // Footer line
    console.log(chalk.gray("─".repeat(60)));
    console.log("\n");

    return fullResponse;

  } catch (error) {
    spinner.error("Failed to get AI response");
    throw error;
  }
}


async function updateConversationTitle(conversationId, userInput, messageCount) {
  if (messageCount === 1) {
    const title = userInput.slice(0, 50) + (userInput.length > 50 ? "..." : "");
    await chatService.updateTitle(conversationId, title);
  }
}

async function chatLoop(conversation) {
  logger.helpBox();

  while( true) {
    const userInput = await text({
      message: chalk.blue("💬  Your message "),
      placeholder : "Type your message ....",
      validate(value) {
        if(!value || value.trim().length === 0){
          return "Message cannot be empty.";
        } 
      },
    });

    // Handle cancellation (Ctrl+C)
    if (isCancel(userInput)) {
      const exitBox = boxen(chalk.yellow("Chat session ended. Goodbye! 👋"), {
        padding: 1,
        margin: 1,
        borderStyle: "round",
        borderColor: "yellow",
      });
      console.log(exitBox);
      process.exit(0);
    }

    // Handle exit command
    if (userInput.toLowerCase() === "exit") {
      const exitBox = boxen(chalk.yellow("Chat session ended. Goodbye! 👋"), {
        padding: 1,
        margin: 1,
        borderStyle: "round",
        borderColor: "yellow",
      });
      console.log(exitBox);
      break;
    }

    // Save user message
    await saveMessage(conversation.id, "user", userInput);

    // Get messages count before AI response
    const messages = await chatService.getMessages(conversation.id);
    
    // Get AI response with streaming and markdown rendering
    const aiResponse = await getAIResponse(conversation.id);

    // Save AI response
    await saveMessage(conversation.id, "assistant", aiResponse);

    // Update title if first exchange
    await updateConversationTitle(conversation.id, userInput, messages.length);

  }
}

export async function startChat(mode="chat", conversationId=null){
  try {
    intro(logger.box("Cli Ai Chat", " let us chat ...."));
    const user = await getUserFromToken();
    const conversation = await initConversation(user.id, conversationId, mode)
    await chatLoop(conversation);

    outro(logger.success("✨ Thanks for Chatting"))
  } catch (error) {
    const errorBox = logger.errorbox(error.message);
    process.exit(1)
  }
}

