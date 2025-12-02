import { NextRequest } from "next/server";
import prisma from "@/lib/prisma";

export async function GET(req: NextRequest) {
  try {
    const token = req.nextUrl.searchParams.get("token");

    if (!token) {
      return Response.json(
        { error: "Token is required" },
        { status: 400 }
      );
    }

    const user = await prisma.user.findFirst({
      where: {
        session: {
          some: {
            token: token,
          },
        },
      },
      select: {
        id: true,
        name: true,
        email: true,
        image: true,
      },
    });

    if (!user) {
      return Response.json(
        { error: "No user found for this token" },
        { status: 404 }
      );
    }

    return Response.json(user);
  } catch (err) {
    console.error(err);
    return Response.json(
      { error: "Server error" },
      { status: 500 }
    );
  }
}
