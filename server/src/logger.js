import chalk from "chalk";
import boxen from "boxen";
import { marked } from "marked";
import TerminalRenderer from "marked-terminal";

// Configure marked to use terminal renderer
marked.use(
  new TerminalRenderer({
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

// ──────────────────────────────
// Display messages in boxes
// ──────────────────────────────
function displayMessages(messages) {
  messages.forEach((msg) => {
    if (msg.role === "user") {
      const userBox = boxen(chalk.white(msg.content), {
        padding: 1,
        margin: { left: 2, bottom: 1 },
        borderStyle: "round",
        borderColor: "blue",
        title: "👤 You",
        titleAlignment: "left",
      });
      console.log(userBox);
    } else {
      // Render markdown for assistant messages
      const renderedContent = marked.parse(msg.content);
      const assistantBox = boxen(renderedContent.trim(), {
        padding: 1,
        margin: { left: 2, bottom: 1 },
        borderStyle: "round",
        borderColor: "green",
        title: "🤖 Assistant",
        titleAlignment: "left",
      });
      console.log(assistantBox);
    }
  });
}

const timestamp = () =>
  chalk.gray(
    `[${new Date().toLocaleTimeString([], { hour12: false })}]`
  );

const logger = {
  // ──────────────────────────────
  // BASIC LOGS
  // ──────────────────────────────
  info: (...msg) =>
    console.log(timestamp(), chalk.blue("ℹ︎ [INFO]"), ...msg),
  success: (...msg) =>
    console.log(timestamp(), chalk.green("✔ [SUCCESS]"), ...msg),
  warn: (...msg) =>
    console.log(timestamp(), chalk.yellow("⚠ [WARN]"), ...msg),
  error: (...msg) =>
    console.log(timestamp(), chalk.red("✖ [ERROR]"), ...msg),

  // ──────────────────────────────
  // TEXT STYLES
  // ──────────────────────────────
  bold: (...msg) => chalk.bold(msg.join(" ")),
  underline: (...msg) => chalk.underline.blue(msg.join(" ")),
  gray: (...msg) => chalk.gray(msg.join(" ")),
  dim: (...msg) => chalk.dim(msg.join(" ")),
  highlight: (...msg) => chalk.bgYellow.black(msg.join(" ")),

  // ──────────────────────────────
  // BOXED OUTPUT
  // ──────────────────────────────
  box: (title, message) => {
  console.log(
    boxen(message, {
      title,
      padding: 2,          // increased padding inside the box
      margin: 1,           // adds space around the box
      borderColor: "cyan",
      borderStyle: "round",
      titleAlignment: "center",
      float: "center",     // optional: center the box horizontally
    })
  );
},


  errorbox: (message) =>
    console.log(
      boxen(chalk.red(`❌ Error : ${message}`), {
        padding: 1,
        margin: 1,
        borderStyle: "round",
        borderColor: "red",
        titleAlignment: "center",
      })
    ),

  // ──────────────────────────────
  // Conversation Info Box
  // ──────────────────────────────
  conversationInfo: (conversation) => {
    console.log(
      boxen(
        `${chalk.bold("Conversation")}: ${conversation.title}\n${chalk.gray(
          "ID: " + conversation.id
        )}\n${chalk.gray("Mode: " + conversation.mode)}`,
        {
          padding: 1,
          margin: { top: 1, bottom: 1 },
          borderStyle: "round",
          borderColor: "cyan",
          title: "💬 Chat Session",
          titleAlignment: "center",
        }
      )
    );
  },

  // ──────────────────────────────
  // Conversation Messages (with boxes & markdown)
  // ──────────────────────────────
  conversationMessages: (messages) => {
    if (!messages || messages.length === 0) return;

    console.log(chalk.yellow("📜 Previous messages:\n"));
    displayMessages(messages);
    console.log("\n");
  },

  // ──────────────────────────────
  // HELP BOX
  // ──────────────────────────────
  helpBox: () => {
    const helpBox = boxen(
      `${chalk.gray('• Type your message and press Enter')}\n` +
      `${chalk.gray('• Markdown formatting is supported in responses')}\n` +
      `${chalk.gray('• Type "exit" to end conversation')}\n` +
      `${chalk.gray('• Press Ctrl+C to quit anytime')}`,
      {
        padding: 1,
        margin: { bottom: 1 },
        borderStyle: "round",
        borderColor: "gray",
        dimBorder: true,
      }
    );
    console.log(helpBox);
  },


  // ──────────────────────────────
  // MARKDOWN LOGGING
  // ──────────────────────────────
  markdown: (mdText) => {
    console.log(marked(mdText));
  },

  // ──────────────────────────────
  // SECTION HEADERS
  // ──────────────────────────────
  section: (title) => {
    console.log(
      "\n" +
        chalk.cyan.bold(
          "── " + title + " ───────────────────────────────"
        )
    );
  },

  // ──────────────────────────────
  // EMPTY LINE
  // ──────────────────────────────
  line: () => console.log(""),
};

export default logger;
export { logger };
