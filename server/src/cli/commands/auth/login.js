import { cancel, confirm, intro, isCancel } from "@clack/prompts";
import { Command } from "commander";
import chalk from "chalk";
import os from "os";
import path from "path";
import { z } from "zod/v4";
import open from "open";

import { deviceAuthorization } from "better-auth/plugins";
import { createAuthClient } from "better-auth/client";
import { logger } from "../../../logger.js";

import yoctoSpinner from "yocto-spinner";


import { CLIENT_ID , DEMO_URL } from "../../../core/config.js";
import { getStoredToken , isTokenExpired, storeToken } from "../../../core/token.js";

const CONFIG_DIR = path.join(os.homedir(), ".better-auth");
const TOKEN_FILE = path.join(CONFIG_DIR, "token.json");


// =============================
// LOGIN ACTION
// =============================
export async function loginAction(opts) {
  intro(logger.info("Auth CLI Login"));

  const schema = z.object({
    serverUrl: z.string().optional(),
    clientId: z.string().optional(),
  });

  const parsed = schema.parse(opts);

  const serverUrl = DEMO_URL //parsed.serverUrl ?? process.env.SERVER_URL;
  const clientId =  CLIENT_ID //parsed.clientId ?? CLIENT_ID;

  logger.info("Server URL:", serverUrl);
  logger.info("Client ID:", clientId);

  const existingToken = await getStoredToken();
  const expired = isTokenExpired();

  if (existingToken && !expired) {
    const shouldReAuth = await confirm({
      message: "Already logged in. Login again?",
      initialValue: false,
    });

    if (isCancel(shouldReAuth) || !shouldReAuth) {
      cancel("Login cancelled");
      process.exit(0);
    }
  }

  const authClient = createAuthClient({
    baseURL:serverUrl,
    plugins:[deviceAuthorization()]
  })

  const spinner = yoctoSpinner({
    text: "Requesting device authorization..."
  });

  spinner.start();

  try {
    const {data, error } = await authClient.device.code({
      client_id: clientId,
      scope: "openid profile email"
    })
    
    spinner.stop()

    logger.error("error : ",error)

    if(error || !data) {
      logger.error(
        `Failded to request device Authorization : ${error.error_description}`
      )

      process.exit(1);
    } 

    logger.info(
      `data : ${data}`
    )

    const {
      device_code,
      user_code,
      verification_uri,
      verification_uri_complete,
      interval = 5,
      expires_in,
    } = data;

    logger.info(
      "Device Authorization required."
    )

    logger.info(
      `Please visit ${chalk.underline.blue(verification_uri || verification_uri_complete)}`
    )

    logger.info(
      `Enter Code : ${chalk.bold.green(user_code)}`
    )

    const shouldOpen = await confirm({
      message: "Open browser automatically.",
      initialValue: true
    })

    if(!isCancel(shouldOpen) && shouldOpen) {
      const uriToOpen =  verification_uri_complete || verification_uri;
      await open(uriToOpen)
    }

     logger.info(
      chalk.gray(
        `Waiting for authorization (expries in ${Math.floor(
          expires_in /60,
        )} minutes) ...`
      )
    );

    const token = await pollForToken(
      authClient,
      device_code,
      clientId,
      interval
    )

    if(token) {
      const saved = await storeToken(token);

      if(!saved) {
        logger.warn("Warning : Could not save authentication token.")
        logger.info("You may need to login again on next use.")
      };
     }

    // get the user data

    outro(logger.success("Login Successfully!"))

    logger.success(`Token saved to : ${TOKEN_FILE}`)

    logger.info("You can use AI command without logging again.");
  } catch (error) {
     
    spinner.stop();
    logger.error(
      `error : ${error}`
    )
  }
}


async function pollForToken(authClient, deviceCode, clientId, interval) {
  let pollingInterval = interval;

  const spinner = yoctoSpinner({
    text: "",
    color: "cyan",
  });

  let dots = 0;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      dots = (dots + 1) % 4;

      spinner.text = chalk.gray(
        `Polling for authorization ${".".repeat(dots)}${" ".repeat(3 - dots)}`
      );

      if (!spinner.isSpinning) spinner.start();

      try {
        const { data, error } = await authClient.device.token({
          grant_type: "urn:ietf:params:oauth:grant-type:device_code",
          device_code: deviceCode,
          client_id: clientId,
          fetchOptions: {
            headers: {
              "user-agent": `My CLI`,
            },
          },
        });

        if (data?.access_token) {
          spinner.stop();
          logger.info(`Your access token: ${data.access_token}`);
          return resolve(data);
        }

        if (error) {
          switch (error.error) {
            case "authorization_pending":
              break;

            case "slow_down":
              pollingInterval += 5;
              break;

            case "access_denied":
              spinner.stop();
              console.error("Access denied by user.");
              return reject(new Error("access_denied"));

            case "expired_token":
              spinner.stop();
              console.error("Device code expired. Start again.");
              return reject(new Error("expired_token"));

            default:
              spinner.stop();
              logger.error(`Error: ${error.error_description}`);
              return reject(new Error(error.error_description));
          }
        }
      } catch (err) {
        spinner.stop();
        logger.error(err);
        return reject(err);
      }

      setTimeout(poll, pollingInterval * 1000);
    };

    setTimeout(poll, pollingInterval * 1000);
  });
}



// =============================
// COMMAND EXPORT
// =============================
export const login = new Command("login")
  .description("Login to Better Auth")
  .option("--server-url <url>", "Better Auth Server URL")
  .option("--client-id <id>", "OAuth Client ID")
  .action(loginAction);
