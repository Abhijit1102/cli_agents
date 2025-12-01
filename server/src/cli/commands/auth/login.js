import { cancel, confirm, intro, isCancel, outro } from "@clack/prompts";
import { Command } from "commander";
import { z } from "zod/v4";
import open from "open";

import { deviceAuthorization } from "better-auth/plugins";
import { createAuthClient } from "better-auth/client";
import { logger } from "../../../logger.js";

import yoctoSpinner from "yocto-spinner";

import { CLIENT_ID, DEMO_URL ,TOKEN_FILE } from "../../../core/config.js";
import { getStoredToken, isTokenExpired, storeToken } from "../../../core/token.js";


// =============================
// LOGIN ACTION
// =============================
export async function loginAction(opts) {
  intro(logger.bold("Auth CLI Login"));

  const schema = z.object({
    serverUrl: z.string().optional(),
    clientId: z.string().optional(),
  });

  const parsed = schema.parse(opts);

  const serverUrl = DEMO_URL;
  const clientId = CLIENT_ID;

  logger.section("Configuration");
  logger.info("Server URL:", logger.gray(serverUrl));
  logger.info("Client ID:", logger.gray(clientId));

  const existingToken = await getStoredToken();
  const expired = isTokenExpired();

  if (existingToken && !expired) {
    const shouldReAuth = await confirm({
      message: "Already logged in. Login again?",
      initialValue: false,
    });

    if (isCancel(shouldReAuth) || !shouldReAuth) {
      cancel(logger.warn("Login cancelled"));
      process.exit(0);
    }
  }

  const authClient = createAuthClient({
    baseURL: serverUrl,
    plugins: [deviceAuthorization()],
  });

  const spinner = yoctoSpinner({ text: "Requesting device authorization..." });

  spinner.start();

  try {
    const { data, error } = await authClient.device.code({
      client_id: clientId,
      scope: "openid profile email",
    });

    spinner.stop();

    if (error || !data) {
      logger.error(
        "Failed to request device Authorization:",
        logger.bold(error.error_description),
      );
      process.exit(1);
    }

    logger.section("Device Authorization");
    logger.success("Device code received!");

    const {
      device_code,
      user_code,
      verification_uri,
      verification_uri_complete,
      interval = 5,
      expires_in,
    } = data;

    logger.info("Please visit:", logger.underline(verification_uri));
    logger.info("Enter Code:", logger.bold(user_code));

    const shouldOpen = await confirm({
      message: "Open browser automatically?",
      initialValue: true,
    });

    if (!isCancel(shouldOpen) && shouldOpen) {
      await open(verification_uri_complete || verification_uri);
    }

    logger.info(
      logger.gray(
        `Waiting for authorization (expires in ${Math.floor(
          expires_in / 60,
        )} minutes)...`,
      ),
    );

    // Polling for token
    const token = await pollForToken(authClient, device_code, clientId, interval);

    if (token) {
      const saved = await storeToken(token);
      if (!saved) {
        logger.warn("Could not save authentication token.");
        logger.info("You may need to login again next time.");
      }
    }

    outro(logger.success("Login Successfully!"));
    logger.success(`Token saved to: ${logger.bold(TOKEN_FILE)}`);
    logger.info("You can now use AI commands without logging in again.");
  } catch (err) {
    spinner.stop();
    logger.error("Unexpected error:", logger.bold(String(err)));
  }
}

// =============================
// POLL FOR TOKEN
// =============================
async function pollForToken(authClient, deviceCode, clientId, interval) {
  let pollingInterval = interval;

  const spinner = yoctoSpinner({
    text: "",
    color: "cyan",
  });

  let dots = 0;

  logger.section("Authorization");

  return new Promise((resolve, reject) => {
    const poll = async () => {
      dots = (dots + 1) % 4;

      spinner.text = logger.gray(
        `Polling for authorization ${".".repeat(dots)}${" ".repeat(3 - dots)}`,
      );

      if (!spinner.isSpinning) spinner.start();

      try {
        const { data, error } = await authClient.device.token({
          grant_type: "urn:ietf:params:oauth:grant-type:device_code",
          device_code: deviceCode,
          client_id: clientId,
          fetchOptions: {
            headers: { "user-agent": "My CLI" },
          },
        });

        if (data?.access_token) {
          spinner.stop();
          logger.success("Authorization completed!");
          logger.info("Access Token:", logger.bold(data.access_token));
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
              logger.error("Access denied by user.");
              return reject(new Error("access_denied"));

            case "expired_token":
              spinner.stop();
              logger.error("Device code expired. Start again.");
              return reject(new Error("expired_token"));

            default:
              spinner.stop();
              logger.error("Error:", logger.bold(error.error_description));
              return reject(new Error(error.error_description));
          }
        }
      } catch (err) {
        spinner.stop();
        logger.error("Polling error:", logger.bold(String(err)));
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
