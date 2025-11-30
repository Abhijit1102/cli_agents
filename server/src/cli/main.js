#!/usr/bin/env node

import dotenv from "dotenv";
import chalk from "chalk";
import figlet from "figlet";
import { Command } from "commander";
import { login } from "./commands/auth/login.js";

dotenv.config();

async function main() {
  // ============================================
  // CLI Banner
  // ============================================
  console.log(
    chalk.cyanBright(
      figlet.textSync("CLI AGENT", {
        font: "Standard",
        horizontalLayout: "default",
        verticalLayout: "default",
      })
    )
  );

  console.log(
    chalk.gray(
      "⚡ A Terminal-based AI Assistant\n"
    )
  );

  // ============================================
  // Commander Setup
  // ============================================
  
  const program = new Command("agent");

  program
    .version("1.0.0")
    .description("🚀 CLI Agent with Tool-based AI capabilities")
    .option("-v, --verbose", "Enable verbose logging");

  // 👉 Register login command properly
  program.addCommand(login);

  // 👉 Default "agent" → show help
  program.action(() => {
    program.help();
  });

  program.parse(process.argv);
}

// ============================================
// Error Handler
// ============================================
main().catch((err) => {
  console.error("\n" + chalk.red.bold("❌ Unexpected Error Occurred:\n"));
  console.error(chalk.red(err?.message || err));
  process.exit(1);
});
