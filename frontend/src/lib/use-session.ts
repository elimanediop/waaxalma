"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, AuthState, isAuthenticationError } from "@/lib/auth";

type SessionStatus = "loading" | "authenticated" | "error";

export function useRequiredSession() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [message, setMessage] = useState("");
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => setAttempt((previous) => previous + 1), []);

  useEffect(() => {
    let active = true;
    api<AuthState>("/auth/me")
      .then((session) => {
        if (!active) return;
        setAuth(session);
        setStatus("authenticated");
        setMessage("");
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (isAuthenticationError(error)) {
          router.replace("/login");
          return;
        }
        setStatus("error");
        setMessage(error instanceof Error ? error.message : "Unable to verify your session.");
      });
    return () => { active = false; };
  }, [attempt, router]);

  return { auth, status, message, retry };
}
