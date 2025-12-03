import { text, isCancel, cancel, intro, outro, multiselect } from "@clack/prompts";
import logger from "../../logger.js"
import yoctoSpinner from "yocto-spinner";
import chalk from "chalk";
import boxen from "boxen";
import {ChatService} from "../../service/chat-sevice.js"
import { getStoredToken } from "../../core/token.js"
import {getMe} from "../../api/user.api.js"
import { marked } from "marked";
import { markedTerminal } from "marked-terminal";

import { AIService } from "../ai/google-service.js";
import { callToolChatAPI } from "../../api/callToolChatApi.js"

import { 
    availableTools,
    getEnabledTools,
    enableTools,
    getEnabledToolNames,
    resetTools
} from "../../core/tool.config.js";


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
const aiService = new AIService();

async function getUserFromToken() {
  const token = await getStoredToken();

  if (!token?.access_token) {
    throw new Error("Not Authenticated. Please run 'agents login' first");
  }

  const spinner = yoctoSpinner({ text: "Authenticating..." }).start();

  const user = await getMe(token); 

  if (!user) {
    spinner.error("User not found");
    throw new Error("User not found. Please login again");
  }

  spinner.success(`Welcome back, ${user.name}`);

  return user;
}

async function selectTools() {
    const toolOptions = availableTools.map(tool => ({
        value: tool.id,
        label: tool.name,
        hint: tool.description,
    }));

    const selectedTools = await multiselect({
        message: chalk.cyan("\n Select tools to enable (Space to select, Enter to confirm):"),
        options: toolOptions,
        required:true
    })

    if(isCancel(selectTools)){
        cancel(chalk.yellow("\n Tool selectes cancelled."))
        process.exit(0)
    }

    enableTools(selectedTools)
    

     // Log if no tools were selected
    if (selectedTools.length === 0) {
        logger.info("\n No tools selected. AI will work without tools. \n");
    } else {
        logger.ToolBox(selectedTools, availableTools);
        return selectedTools.length > 0;
    }
}

async function initConversation(userId, conversationId=null, mode="tool") {
    const spinner = yoctoSpinner({ "text": "Loading Conversation..." }).start();

    const conversation = await chatService.getOrCreateConversation(
        userId,
        conversationId,
        mode
    )

    spinner.success("Conversation Loaded!..")

    const enabledToolNames = getEnabledToolNames();
    
    const toolsDisplay = enabledToolNames.length > 0 
        ? `\n${chalk.gray("Active Tools:")} ${enabledToolNames.join(", ")}`
        : `\n${chalk.gray("No tools enabled")}`;

    
    logger.conversationInfoToolCalling(conversation, getEnabledTools(), availableTools)

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

  const tools = getEnabledTools();
  
    const apiResponse = await callToolChatAPI({ messages: aiMessages, tools });
    spinner.stop();

    // Render markdown in terminal
    console.log(marked.parse(apiResponse.content));

    return apiResponse.content;
}

async function updateConversationTitle(conversationId, userInput, messageCount) {
  if (messageCount === 1) {
    const title = userInput.slice(0, 50) + (userInput.length > 50 ? "..." : "");
    await chatService.updateTitle(conversationId, title);
  }
}

async function chatLoop(conversation) {
    const enabledToolNames = getEnabledToolNames();
    const helpBox = boxen(
        `${chalk.gray('• Type your message and press Enter')}
        \n${chalk.gray('• AI has access to:')} ${enabledToolNames.length > 0 ? enabledToolNames.join(", ") : "No tools"}
        \n${chalk.gray('• Type "exit" to end conversation')}
        \n${chalk.gray('• Press Ctrl+C to quit anytime')}`,
        {
        padding: 1,
        margin: { bottom: 1 },
        borderStyle: "round",
        borderColor: "gray",
        dimBorder: true,
        }
    );
    
  console.log(helpBox);

   while (true) {
    const userInput = await text({
      message: chalk.blue("💬 Your message"),
      placeholder: "Type your message...",
      validate(value) {
        if (!value || value.trim().length === 0) {
          return "Message cannot be empty";
        }
      },
    });

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

    const userBox = boxen(chalk.white(userInput), {
      padding: 1,
      margin: { left: 2, top: 1, bottom: 1 },
      borderStyle: "round",
      borderColor: "blue",
      title: "👤 You",
      titleAlignment: "left",
    });
    console.log(userBox);

    await saveMessage(conversation.id, "user", userInput);
    const messages = await chatService.getMessages(conversation.id);
    const aiResponse = await getAIResponse(conversation.id);
    await saveMessage(conversation.id, "assistant", aiResponse);
    await updateConversationTitle(conversation.id, userInput, messages.length);
  }
}
     
export async function startToolChat(conversationId = null) {
    try {
       intro(logger.box("🤖 Agentic Intelligence Online  🚀", " ⏳ Tool calling systems initialized…"));
       const user = await getUserFromToken();
      
       await selectTools();

       const coversation = await initConversation(user.id, conversationId, "tool" )

       await chatLoop(coversation);

       resetTools();

       outro(logger.success("🧠 Thanks for using tools calling..."))
    } catch (error) {
        logger.error(`❌  Error... : ${error.message}`)
        
    }
}
