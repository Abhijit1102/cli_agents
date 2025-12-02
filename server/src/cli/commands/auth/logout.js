import { cancel, confirm, intro, isCancel, outro } from "@clack/prompts"
import { logger } from "../../../logger.js";
import { clearStoredToken, getStoredToken } from "../../../core/token.js";
import { Command } from "commander";

export async function logoutAction(){
    intro(logger.bold("Logout"));

    const token = await getStoredToken();

    if (!token) {
        logger.warn("You're not logged in.");
        process.exit(1);
    }

    const shouldLogout = await confirm({
        message: "Are you sure you want to logout!",
        initialValue: false,
    })

    if(isCancel(shouldLogout) || !shouldLogout){
        cancel("Logout cancelled");
        process.exit(1);
    }

    const cleared = await clearStoredToken();

    if(cleared){
        outro(logger.info("Successfully logged out!"))
    } else {
        logger.warn("Could not clear token file.")
    }

}

export const logout = new Command("logout")
  .description("Login to Better Auth")
  .option("--server-url <url>", "Better Auth Server URL")
  .option("--client-id <id>", "OAuth Client ID")
  .action(logoutAction);