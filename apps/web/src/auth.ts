import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import Credentials from "next-auth/providers/credentials";

import { authenticateDemoAccount, demoAccountById } from "@/lib/demo-accounts";
import { syncGoogleIdentity } from "@/lib/internal-api";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google,
    Credentials({
      name: "Cuenta demo SIC",
      credentials: {
        username: { label: "Usuario", type: "text" },
        password: { label: "Contraseña", type: "password" },
      },
      authorize(credentials) {
        const account = authenticateDemoAccount(credentials?.username, credentials?.password);
        return account ? { id: account.id, name: account.name, email: account.email } : null;
      },
    }),
  ],
  pages: {
    signIn: "/ingresar",
  },
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async signIn({ account, profile }) {
      if (account?.provider === "credentials") return true;
      return account?.provider === "google" && Boolean(profile?.email && profile.email_verified);
    },
    async jwt({ token, account, profile, user }) {
      token.internalSessionId ??= crypto.randomUUID();
      if (account?.provider === "google" && profile?.sub && profile.email && profile.name) {
        const user = await syncGoogleIdentity({ googleSubject: profile.sub, email: profile.email, name: profile.name, avatarUrl: typeof profile.picture === "string" ? profile.picture : null });
        if (user.status !== "ACTIVE") throw new Error("SIC account is not active");
        token.userId = user.id;
        token.roles = user.roles;
      }
      if (account?.provider === "credentials" && user?.id) {
        const demo = demoAccountById(user.id);
        if (!demo) throw new Error("SIC demo account is not available");
        token.userId = demo.id;
        token.roles = demo.roles;
        token.isDemo = true;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = String(token.userId ?? "");
        session.user.roles = Array.isArray(token.roles) ? token.roles.map(String) : [];
      }
      session.internalSessionId = String(token.internalSessionId ?? "");
      session.isDemo = token.isDemo === true;
      return session;
    },
  },
});
