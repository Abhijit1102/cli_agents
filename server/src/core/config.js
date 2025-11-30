import os from "os";
import path from "path";
import dotenv from "dotenv";
dotenv.config();

export const CONFIG_DIR = path.join(os.homedir(), ".better-auth");
export const TOKEN_FILE = path.join(CONFIG_DIR, "token.json");

export const DEMO_URL = "http://localhost:3000/api/auth";
export const CLIENT_ID = "Ov23liYJoHqtr2Ot80Ml" // process.env.GITHUB_CLIENT_ID;
