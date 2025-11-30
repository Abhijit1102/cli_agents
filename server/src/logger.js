import chalk from "chalk";
import boxen from "boxen";

const timestamp = () =>
  chalk.gray(`[${new Date().toLocaleTimeString([], { hour12: false })}]`);

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
  // TEXT STYLES (return styled strings)
  // ──────────────────────────────
  bold: (...msg) => chalk.bold(msg.join(" ")),
  underline: (...msg) => chalk.underline.blue(msg.join(" ")),
  gray: (...msg) => chalk.gray(msg.join(" ")),
  dim: (...msg) => chalk.dim(msg.join(" ")),
  highlight: (...msg) => chalk.bgYellow.black(msg.join(" ")),

  // ──────────────────────────────
  // BOXED OUTPUT (title or message)
  // ──────────────────────────────
  box: (title, message) => {
    console.log(
      boxen(message, {
        title,
        padding: 1,
        borderColor: "cyan",
        borderStyle: "round",
      })
    );
  },

  // ──────────────────────────────
  // SECTION HEADERS
  // ──────────────────────────────
  section: (title) => {
    console.log(
      "\n" +
        chalk.cyan.bold("── " + title + " ───────────────────────────────")
    );
  },

  // ──────────────────────────────
  // EMPTY LINE (for formatting)
  // ──────────────────────────────
  line: () => console.log(""),
};

export default logger;
export { logger };
