import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

// Convert handler
const handlerObj = toNextJsHandler(auth.handler);

// // Log the output
// console.log("toNextJsHandler output:", handlerObj);

export const { GET, POST } = handlerObj;
