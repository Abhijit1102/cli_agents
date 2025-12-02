import chalk from "chalk";
import { logger } from "../../../logger.js";
import { requireAuth } from "../../../core/token.js";
import { Command } from "commander";
import { getMe } from "../../../api/user.api.js"; 
export async function whoamiAction() {
  try {
    const token = await requireAuth();

    logger.info(chalk.gray("Fetching your profile..."));

    // 🌐 Use getMe from user.api.js
    const user = await getMe(token);

    console.log(""); // spacing
    console.log(chalk.green.bold("✓ Authenticated User"));
    console.log(chalk.white("───────────────"));
    console.log(chalk.cyan("ID:      ") + chalk.white(user.id));
    console.log(chalk.cyan("Email:   ") + chalk.white(user.email));
    console.log(chalk.cyan("Name:    ") + chalk.white(user.name || "N/A"));
    console.log(""); // spacing
  } catch (error) {
    const msg = error?.response?.data?.error || error.message;
    logger.error(`Failed to fetch user info: ${msg}`);
  }
}

export const whoami = new Command("whoami")
  .description("Show the current authenticated user")
  .option("--server-url <url>", "Better Auth Server URL")
  .option("--client-id <id>", "OAuth Client ID")
  .action(whoamiAction);
