import fs from "fs/promises";
import { CONFIG_DIR, TOKEN_FILE } from "./config.js";
import logger from "../logger.js"

export async function getStoredToken() {
  try {
    const raw = await fs.readFile(TOKEN_FILE, "utf-8");
    return JSON.parse(raw);
  } catch (error){
    logger.error(
        `Error in accessing Token.. ${error}`
    )
    return null;
  }
}

export async function storeToken(token) {
  try {
    await fs.mkdir(CONFIG_DIR, { recursive: true });

    const data = {
      access_token: token.access_token,
      refresh_token: token.refresh_token,
      token_type: token.token_type || "Bearer",
      scope: token.scope,
      created_at: new Date().toISOString(),
      expires_at: token.expires_in
        ? new Date(Date.now() + token.expires_in * 1000).toISOString()
        : null,
    };

    await fs.writeFile(TOKEN_FILE, JSON.stringify(data, null, 2), "utf-8");
    return true;
  } catch (e) {
    logger.error("Failed to store token:", e.message);
    return false;
  }
}

export async function clearStoredToken() {
  try {
    await fs.unlink(TOKEN_FILE);
    return true;
  } catch (error){
    logger.error(
        `Error in removing Token ${error}`
    )
    return false;
  }
}

export async function isTokenExpired() {
  const token = await getStoredToken();
  if (!token?.expires_at) return true;

  const now = new Date();
  const expires = new Date(token.expires_at);

  return expires.getTime() - now.getTime() < 5 * 60 * 1000;
}

export async function requireAuth() {
  const token = await getStoredToken();

  if (!token) {
    logger.error("❌ Not authenticated. Run: agent login");
    process.exit(1);
  }

  if (await isTokenExpired()) {
    logger.error("⚠️ Session expired. Run: agent login");
    process.exit(1);
  }

  return token;
}

