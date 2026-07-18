import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

import { syncGoogleIdentity } from "@/lib/internal-api";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google],
  pages: {
    signIn: "/ingresar",
  },
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async signIn({ account, profile }) {
      if (account?.provider !== "google") return false;
      return Boolean(profile?.email && profile.email_verified);
    },
    async jwt({ token, account, profile }) {
      token.internalSessionId ??= crypto.randomUUID();
      if (account?.provider === "google" && profile?.sub && profile.email && profile.name) {
        const user = await syncGoogleIdentity({ googleSubject: profile.sub, email: profile.email, name: profile.name, avatarUrl: typeof profile.picture === "string" ? profile.picture : null });
        if (user.status !== "ACTIVE") throw new Error("SIC account is not active");
        token.userId = user.id;
        token.roles = user.roles;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = String(token.userId ?? "");
        session.user.roles = Array.isArray(token.roles) ? token.roles.map(String) : [];
      }
      session.internalSessionId = String(token.internalSessionId ?? "");
      return session;
    },
  },
});
