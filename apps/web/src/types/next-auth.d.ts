import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    internalSessionId: string;
    user: DefaultSession["user"] & {
      id: string;
      roles: string[];
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    userId?: string;
    roles?: string[];
    internalSessionId?: string;
  }
}
