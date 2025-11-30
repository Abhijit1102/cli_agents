import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { PrismaClient } from "@prisma/client";
import { deviceAuthorization } from "better-auth/plugins"; 


const prisma = new PrismaClient();

export const auth = betterAuth({
  database: prismaAdapter(prisma, { provider: "postgresql" }),

  baseURL: "http://localhost:3005",
  basePath: "/api/auth",
  trustedOrigins: ["http://localhost:3000"],

  plugins: [
    deviceAuthorization({ 
      verificationUri: "http://localhost:3005/api/auth/device", 
    }), 
  ],

  socialProviders: {
    github: {
      clientId: process.env.GITHUB_CLIENT_ID,
      clientSecret: process.env.GITHUB_CLIENT_SECRET,
    },
  },
});
